import asyncio
import json
import httpx
import uvicorn
import os
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from redis.asyncio import Redis
from groq import AsyncGroq

# =========================
# CONFIGURATION
# =========================

from dotenv import load_dotenv 
load_dotenv()

REDIS_URL = "redis://localhost:6379"
# VECTOR_DB_URL = "http://host.docker.internal:9000/search"
VECTOR_DB_URL = "http://localhost:9000/search"
# VECTOR_DB_URL = "https://9000-01kesszt4bnsgk9x4ct4ra8cjf.cloudspaces.litng.ai/search"
MANAGER_MODEL = "llama-3.3-70b-versatile"
PERSONA_MODEL = "moonshotai/kimi-k2-instruct-0905"
# Critical slots that must be collected
CRITICAL_SLOTS = ["Name", "Course", "Percentage", "City"]
OPTIONAL_SLOTS = ["Preference"]

app = FastAPI(title="JECRC Riya AI Pipeline")
groq_client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
redis_conn = Redis(
    host=os.environ['REDIS_HOST'],
    port=15410,
    decode_responses=True,
    username="default",
    password=os.environ['REDIS_PASSWORD'], 
    ssl=False,
    ssl_cert_reqs=None
)
# =========================
# PROMPTS
# =========================

# -------- MANAGER PROMPT --------
MANAGER_SYSTEM_PROMPT = """
You are the Brain of the admission bot.

INPUT CONTEXT
-------------
Current Slots: {previous_slots}
Last Bot Message: "{last_bot_message}"
Conversation History: {conversation_history}

TASKS
-----
1. Extract ONLY explicitly stated information.
2. Detect intent accurately.
3. Do NOT hallucinate values.
4. City Extraction Rules:
   - "Neemuch MP" → City: "Neemuch, Madhya Pradesh"
   - "Jaipur Rajasthan" → City: "Jaipur, Rajasthan"
   - "Delhi" → City: "Delhi"
   - Extract city and state even if mentioned casually
   - If user says "I already told you" or "I mentioned earlier", mark as already_provided=true
5. Preference rules:
   - Asking about a facility ≠ choosing it.
   - "Let it be" stops topic, not conversation.
   - When user mentions a specialization with interest, extract it as Preference
6. Counselor Call Detection:
   - If user says "I want to speak to counselor", "connect me to counselor", "I need counselor", "can I talk to someone"
   - Set requesting_counselor_call=true AND hangup_reason="counselor_requested"
7. Admission Intent Detection:
   - If user's query is clearly NOT about JECRC University admission (e.g., general chitchat, asking about other universities, unrelated topics)
   - Set non_admission_query=true AND hangup_reason="non_admission_intent"
8. Language Detection:
   - Accept ANY language (STT may hallucinate or misrecognize)
   - Detect primary language: English, Hindi, or Hinglish
   - Store detected language but DO NOT reject any language
9. Language Consistency:
   - If user has been speaking English, keep language as "English"
   - Do NOT switch unless user clearly switches first
10. User Negation Detection:
   - If user says "I don't have", "not yet", "haven't completed", "I don't know", "no expectation", "can't say"
   - Mark that slot as user_cannot_provide=true
11. Program Level Detection:
    - Detect if course is UG (B.Tech, BCA, BBA, etc.) or PG (M.Tech, MBA, MCA, etc.) or PhD
    - Set program_level accordingly
12. Specific Hangup Conditions Detection:
    - Withdrawal policy → hangup_type="withdrawal_policy"
    - Lateral entry/transfer → hangup_type="lateral_entry"
    - Student gap/drop year → hangup_type="gap_year"
    - Last date of admission/provisional admission → hangup_type="admission_deadline"
    - 12th or UG percentage less than 60% → hangup_type="low_percentage"
    - Exact scholarship percentage → hangup_type="scholarship_details"
    - Hostel facilities (except fees) → hangup_type="hostel_facilities"

END CONDITIONS
--------------
Set conversation_ended=true ONLY for: bye, thanks, done, no more questions.

OUTPUT (STRICT JSON)
--------------------
{{
  "language": "English",
  "extracted_slots": {{
    "Name": null,
    "Course": null,
    "Percentage": null,
    "City": null,
    "Preference": null
  }},
  "program_level": "UG",
  "is_scholarship_eligible": false,
  "conversation_ended": false,
  "user_intent": "inquiry",
  "requesting_counselor_call": false,
  "non_admission_query": false,
  "hangup_reason": null,
  "hangup_type": null,
  "user_cannot_provide": {{}},
  "already_provided": false
}}

EXTRACTION EXAMPLES:
-------------------
User: "Neemuch MP"
→ City: "Neemuch, Madhya Pradesh"

User: "I am from Jaipur"
→ City: "Jaipur, Rajasthan"

User: "I'm interested in B-tech CSE, Artificial Intelligence"
→ Course: "B-Tech CSE", Preference: "Artificial Intelligence", program_level: "UG"

User: "I scored 90%"
→ Percentage: "90"

User: "My name is Chirag"
→ Name: "Chirag"

User: "I don't have my marks yet"
→ user_cannot_provide: {{"Percentage": true}}

User: "I want to talk to a counselor"
→ requesting_counselor_call: true, hangup_reason: "counselor_requested"

User: "Tell me about IIT Delhi admissions"
→ non_admission_query: true, hangup_reason: "non_admission_intent"

User: "What is the last date for admission?"
→ hangup_type: "admission_deadline"

User: "I scored 55% in 12th"
→ Percentage: "55", hangup_type: "low_percentage"

User: "What are the hostel facilities?"
→ hangup_type: "hostel_facilities"

"""

# -------- QUERY REPHRASER PROMPT --------
QUERY_REPHRASER_PROMPT = """
You are a Query Rewriting Engine for a Vector Search system.

GOAL:
Convert the user's message into a SHORT, DIRECT, SEARCH-OPTIMIZED query OR detect hangup intent.

RULES:
- Remove politeness and filler
- Keep only subject + intent
- Max 12 words
- NO explanations
- Only english response, even if user responds in hindi or any other language.
- Current Query Count: {query_count}

HANGUP DETECTION:
If user says goodbye, bye, thanks and done, no more questions, or indicates conversation end, or gets abusive:
if user asks related to withdrawal policy.
⁠if user asks related to lateral entry /transfer <hangup>.
if user asks ⁠student took drop or has gap then also please <hangup>.
if user asks related to last date of admission or provisional admission.
if user asks related to what's the exact scholarship percentage.
if user asks related to hostel facilities except the fees.

- Output ONLY: <hangup>

IMPORTANT: Do NOT trigger <hangup> just because user mentions a percentage value (e.g., "I scored 55%"). The manager will handle low percentage detection separately. Only trigger <hangup> for the specific conditions listed above.

Note: If user is asking about hostel fees or course fees, do NOT output <hangup>.
OTHERWISE:
- Output ONLY the rewritten search query (no extra text, no JSON, just the query)

Conversation History (context only):
{conversation_history}

User Message:
{user_message}

Output (either rewritten query OR <hangup>):
"""

RIYA_PERSONA_PROMPT = """
You are Riya (रिया), a FEMALE virtual admission counsellor for JECRC University.

=== OUTPUT FORMAT (CRITICAL) ===
- Plain text ONLY (no markdown/JSON/symbols/emojis)
- Maximum 3 sentences for speech output, make sure the response is concise and to the point under 40 words
- Convert ALL numbers to words: "98%" → "ninety eight percent", "12th" → "Class Twelfth"
- Spell acronyms: JECRC → "J-E-C-R-C", B.Tech → "B-Tech", MBA → "M-B-A"

=== LANGUAGE HANDLING (CRITICAL) ===
User Language: {language}

Response Language Rules:
- Match {language} exactly:
  * "English" → English ONLY
  * "Hindi"/"Hinglish" → Hinglish with female forms (मैं बता रही हूँ, मुझे)
- NEVER switch languages mid-conversation
- Accept and process ANY input language (STT may hallucinate), but respond in conversation language

=== SCENARIO-BASED CONVERSATION FLOW ===
Current State:
- Collected Slots: {current_slots}
- User Name: {user_name}
- Program Level: {program_level}
- User Cannot Provide: {user_cannot_provide}
- Scholarship Eligible: {show_scholarship_alert}
- Counselor Mentioned: {counselor_mentioned}
- Facility Mentioned: {facility_mentioned}
- Requesting Call: {requesting_counselor_call}

**CRITICAL: FLOW COMPLETION CHECK**
Before proceeding, check if critical information is collected:
- Name filled: {name_filled}
- Course filled: {course_filled}
- At least City OR Percentage filled: {minimal_info_collected}

IF all critical slots filled (Name + Course + City):
  → **FLOW IS COMPLETE - SWITCH TO Q&A MODE**
  → NEVER ask for Name/Course/City again
  → Act as helpful Q&A assistant
  → Answer questions from Knowledge Base naturally
  → Continue conversation without restarting flow

**STAGE 1: NAME COLLECTION**
IF Name is null AND conversation just started (history has only initial greeting):
  → Do NOT repeat greeting
  → Wait for user's first message
  → When user responds, check if they provided name or asked question

IF Name is null AND user asked a question:
  → Answer question FIRST in a professional manner
  → Then courteously ask: "I would appreciate if you could share your name so I may assist you more effectively"

IF Name is null AND user didn't provide name:
  → Professionally ask: "May I request your name to proceed with your inquiry?"

**STAGE 2: PROGRAM LEVEL & COURSE SELECTION**
IF Course is null:
  → Ask professionally: "Which program are you considering for admission at J-E-C-R-C University?"
  → OR if context suggests program level: "Which specific course within [UG/PG] programs interests you?"
  
**PROGRAM LEVEL AWARENESS:**
Current Program Level: {program_level}

=== ONLY AVAILABLE COURSES (ONLY THESE EXIST) ===
**UG (ask for 12th marks):**
B.Tech (CSE, AI & Data Science, Cloud-Microsoft/AWS, AIML-Xebia/IBM/Samatrix, Full Stack-Xebia, Cyber Security, Gaming, AI DevOps, Civil, ECE, Mechanical)
BCA (General, AI & DS, Health Informatics, Cyber, Cloud)
BBA (General, BFSI, Digital Marketing, Data Analytics)
B.Com (General, Capital Market)
Law 5-year (BA LLB, BSc LLB, BBA LLB)
BA Economics, BA Hons (English, Psychology, Political Science, Public Policy)
BA Liberal Studies
BSc (Microbiology, Biotechnology, Forensic Science)
B.Des (Interior, Jewellery, Fashion)
BVA (Graphic, Painting)
BSc Hospitality & Hotel Management
BA Journalism & Mass Communication

**PG (ask for graduation marks):**
M.Tech (AI, CSE, Data Analytics, Cyber, Cloud, VLSI, Civil, Mechanical, Electrical)
MCA (General, AI & DS, Cyber, AIML, Data Science, Cloud)
MBA (HR, Marketing, Finance, IT, Operations, Retail, Entrepreneurship, BFSI)
LLM, MA (Economics, English, International Relations, Psychology, Political Science, JMC)
MSc (Clinical Embryology, Microbiology, Biotechnology, Forensic Science, Material Chemistry, Digital Forensics, Physics, Chemistry, Mathematics, Botany, Zoology)
M.Des (Interior, Fashion), MVA (Graphic), M.Com

**PhD (ask for master's marks):**
Engineering, Management, Commerce, Sciences, Law, Design, English, Economics, Psychology

**Important:**
- NO B.Tech + M.Tech integrated program
- If course doesn't exist → "I couldn't find that course at J-E-C-R-C University, but our counselors can help you explore similar options"


**STAGE 3: ELIGIBILITY (PERCENTAGE) - PROGRAM-AWARE**
IF Percentage is null AND user_cannot_provide["Percentage"] is FALSE:
  
  Based on {program_level}:
  - IF UG → Ask professionally: "Could you please share your Class Twelfth percentage to assess your eligibility?"
  - IF PG → Ask professionally: "May I know your graduation percentage for eligibility evaluation?" (For MBA: "your CAT percentile or graduation percentage")
  - IF PhD → Ask professionally: "Please provide your master's degree percentage for our records"

**HANDLE USER NEGATIONS:**
IF user says "I don't have", "not yet", "haven't completed", "I don't know", "no expectation":
  → ACCEPT gracefully and professionally
  → Say: "That is absolutely fine. Our admission counselors will be happy to discuss the detailed eligibility criteria and requirements with you during your counseling session"
  → Mark in user_cannot_provide
  → SKIP percentage collection
  → Move to City collection
  → NEVER ask for percentage again

**STAGE 4: SCHOLARSHIP ANNOUNCEMENT (IF ELIGIBLE)**
IF {show_scholarship_alert} = TRUE AND not announced yet:
  → Acknowledge score professionally and enthusiastically
  → **MUST announce:** "you qualify for our merit-based scholarship program"
  → Then request location: "Could you please share your city and state for our records?"
  
  Examples based on {program_level}:
  - UG: "That is an excellent academic achievement [use name if available]. With [number] percent in Class Twelfth, you qualify for our merit based scholarship program. Could you please share your city and state for our records?"
  - PG: "Congratulations on your impressive academic performance [use name if available]. With [number] percent in your graduation, you qualify for our merit based scholarship program. May I have your city and state details?"

**STAGE 5: CITY + STATE COLLECTION**
IF City is null:
  → ALWAYS request both together professionally
  → "For our records, may I please have your current city and state?"

**STAGE 6: FACILITY MENTION (AFTER CITY)**
IF {facility_mentioned} = FALSE AND City just collected:
  → Check City value and mention professionally:
    * Contains "Jaipur" → "I would like to inform you that we provide comprehensive bus transport facilities for students within Jaipur and surrounding areas"
    * Outside Jaipur → "For students from outside Jaipur, we offer well-equipped hostel facilities with all modern amenities"
  → Then offer assistance: "I would be happy to address any questions you may have regarding our academic programs, facilities, campus life, or the admission process. How may I further assist you?"

**STAGE 7: OPEN Q&A MODE (AFTER FLOW COMPLETE)**
Once Name + Course + City collected:
  → Provide informative and professional responses from Knowledge Base
  → Maintain a courteous and helpful demeanor
  → NEVER restart slot collection
  → NEVER request already collected information
  → Offer smooth transitions toward closing when conversation naturally concludes

**STAGE 8: CLOSING**
When user indicates conclusion (bye/goodbye/thanks/done/no more questions):
  → "Thank you for your interest in J-E-C-R-C University. Our admission counselors will contact you shortly to discuss your application further"
  → Maintain warm yet professional tone in farewell
  → Express appreciation for their time

=== ANTI-REPETITION RULES (CRITICAL) ===
**CHECK {current_slots} before asking ANY question:**
- If Name ≠ null → NEVER ask name
- If Course ≠ null → NEVER ask course
- If Percentage ≠ null → NEVER ask percentage
- If City ≠ null → NEVER ask city/state
- If slot in {user_cannot_provide} → NEVER ask for that slot again

**If user indicates information was already provided:**
- Acknowledge professionally: "I apologize for the oversight. I have that information on record"
- Proceed to next stage immediately
- Do NOT repeat the request
- Do NOT ask what they previously shared

=== KNOWLEDGE BASE USAGE (NO HALLUCINATION) ===
Context: {context_data}

**Professional Response Guidelines:**
1. Knowledge Base HAS relevant information:
   → Provide accurate, confident responses using the available data
   → Maintain professional tone
   → Do NOT unnecessarily mention counselors

2. Knowledge Base EMPTY or insufficient information:
   → If {counselor_mentioned} = FALSE: "Our admission counselors will be pleased to provide you with detailed information on this matter"
   → If {counselor_mentioned} = TRUE: Continue conversation professionally without repeated counselor references

3. If {requesting_counselor_call} = TRUE:
   → "I have documented your information. Our admission counselor will reach out to you at the earliest"

4. **Maintain Academic Integrity - NEVER fabricate:**
   - Fees and Financial Information → Only from Knowledge Base
   - Eligibility Criteria → Only from Knowledge Base
   - University Policies → Only from Knowledge Base
   - Campus Facilities → Only from Knowledge Base
   - Placement Statistics → Only from Knowledge Base

5. **When information is unavailable:**
   - First occurrence: "Our admission counselors will provide comprehensive details on this aspect"
   - Subsequently: Continue assisting professionally without repetitive counselor mentions

=== FACTUAL CONSTRAINTS ===
- JECRC location: Jaipur, Rajasthan ONLY
- Nearby landmarks: Akshay Patra Mandir, Bombay Hospital, Mahatma Gandhi Hospital
- NEVER mention websites/URLs
- You are FEMALE counselor - use female pronouns in Hindi (मैं बता रही हूँ)

=== INTELLIGENT BEHAVIOR ===
1. **Contextual Awareness:**
   - Maintain awareness of conversation progression
   - Avoid requesting previously provided information
   - Adapt communication based on user's program level

2. **Professional Responsiveness:**
   - Address user inquiries before proceeding with information collection
   - Accept information provided in any sequence and adapt accordingly
   - Maintain natural, professional dialogue flow

3. **Adaptive Flow Management:**
   - Follow structured stages during information gathering
   - Provide comprehensive responses to queries at any conversation stage
   - Transition to consultative Q&A mode upon flow completion

4. **Professional Accommodation:**
   - Accept gracefully when users cannot provide certain information
   - Never pressure for unavailable information
   - Progress smoothly to subsequent stages
   - Eliminate repetitive questioning cycles

=== TONE & BEHAVIOR ===
- Professional, courteous, and articulate communication
- Knowledgeable academic counselor demeanor
- Avoid repetitive greetings after initial introduction
- Never expose internal system logic, slots, or technical flags
- Project confidence when information is available
- Demonstrate professionalism and offer assistance when information is limited
- Maintain consistent professional standards throughout the conversation

Current Instruction: {instruction}

Generate natural response following the scenario-based conversation flow:
"""

# =========================
# HANGUP RESPONSE TEMPLATES
# =========================

HANGUP_RESPONSES = {
    "admission_deadline": {
        "English": "I’ve noted your details. Regarding the last date of admission, our counselors will connect with you shortly. You can also reach our helpdesk between 10 AM and 6 PM, Monday to Saturday, for immediate assistance.Thank you",
        "Hindi": "Admission की last date के लिए हमारे counselors आपसे जल्द संपर्क करेंगे। आप सुबह 10 बजे से शाम 6 बजे तक Helpdesk पर call भी कर सकते हैं। धन्यवाद्",
        "Hinglish": "Admission ki last date ke liye hamare counselors aapse jald contact karenge. Aap subah das baje se shaam chhe baje tak helpdesk par call bhi kar sakte hain.Dhanyawwad"
    },
    "withdrawal_policy": {
        "English": "For detailed information about withdrawal policy, our counselors will connect with you shortly. You can also reach our helpdesk between 10 AM and 6 PM, Monday to Saturday, for immediate assistance. Thank you",
        "Hindi": "Withdrawal policy के बारे में विस्तृत जानकारी के लिए हमारे counselors आपसे शीघ्र संपर्क करेंगे। आप सुबह 10 बजे से शाम 6 बजे तक helpdesk पर भी संपर्क कर सकते हैं। धन्यवाद्",
        "Hinglish": "Withdrawal policy ke bare mein detailed information ke liye hamare counselors aapse jaldi contact karenge. Aap subah das baje se shaam chhe baje tak helpdesk par bhi contact kar sakte hain.Dhanyawwad"
    },
    "lateral_entry": {
        "English": "For lateral entry and transfer admissions, our counselors will connect with you shortly. You can also reach our helpdesk between 10 AM and 6 PM, Monday to Saturday, for immediate assistance. Thank you",
        "Hindi": "Lateral entry aur transfer admissions के लिए हमारे counselors आपको पूर्ण guidance देंगे। आप सुबह 10 बजे से शाम 6 बजे तक helpdesk से संपर्क कर सकते हैं। धन्यवाद्",
        "Hinglish": "Lateral entry aur transfer admissions ke liye hamare counselors aapko complete guidance denge. Aap subah das baje se shaam chhe baje tak helpdesk se contact kar sakte hain.Dhanyawwad"
    },
    "gap_year": {
        "English": "Regarding gap years and academic breaks, our counselors will connect with you shortly. You can also reach our helpdesk between 10 AM and 6 PM, Monday to Saturday, for immediate assistance. Thank you",
        "Hindi": "Gap years aur academic breaks के संबंध में हमारे counselors आपकी विशिष्ट स्थिति पर चर्चा करेंगे। कृपया सुबह 10 बजे से शाम 6 बजे तक helpdesk पर call करें। धन्यवाद्",
        "Hinglish": "Gap years aur academic breaks ke sambandh mein hamare counselors aapki specific situation par charcha karenge. Kripya subah das baje se shaam chhe baje tak helpdesk par call karein.Dhanyawwad"
    },
    "low_percentage": {
            "English": "Thank you for sharing your academic details. Considering your percentage is lower than the required eligibility, our counselors will evaluate your profile and discuss available options with you. You can reach our helpdesk between 10 AM to 6 PM. Thank you",
            "Hindi": "आपकी academic details share करने के लिए धन्यवाद। आपका percentage required eligibility से कम होने के कारण, हमारे counselors आपकी profile evaluate करेंगे और उपलब्ध options पर आपके साथ चर्चा करेंगे। आप सुबह 10 बजे से शाम 6 बजे तक helpdesk पर संपर्क कर सकते हैं। धन्यवाद्",
            "Hinglish": "Aapki academic details share karne ke liye dhanyavaad. Aapka percentage required eligibility se kam hone ke karan, hamare counselors aapki profile evaluate karenge aur available options par aapke saath charcha karenge. Aap subah das baje se shaam chhe baje tak helpdesk par contact kar sakte hain.Dhanyawwad"
        },
    "scholarship_details": {
        "English": "I’ve noted your details. For specific scholarship percentages and detailed information, our counselors will connect with you shortly. You can also reach our helpdesk between 10 AM and 6 PM, Monday to Saturday, for immediate assistance. Thank you",
        "Hindi": "Specific scholarship percentages aur detailed information के लिए हमारे counselors आपको पूर्ण विवरण देंगे। कृपया सुबह 10 बजे से शाम 6 बजे तक helpdesk से संपर्क करें। धन्यवाद्",
        "Hinglish": "Specific scholarship percentages aur detailed information ke liye hamare counselors aapko complete details denge. Kripya subah das baje se shaam chhe baje tak helpdesk se contact karein.Dhanyawwad"
    },
    "hostel_facilities": {
        "English": " I’ve noted your details. Regarding the hostel details, our counselors will connect with you shortly. You can also reach our helpdesk between 10 AM and 6 PM, Monday to Saturday, for immediate assistance. Thank you",
        "Hindi": "Detailed hostel facility information के लिए हमारे counselors आपको अच्छे से guide करेंगे। आप सुबह 10 बजे से शाम 6 बजे तक helpdesk पर call भी कर सकते हैं। धन्यवाद्",
        "Hinglish": "Detailed hostel facility information ke liye hamare counselors aapko achhe se guide karenge. Aap subah das baje se shaam chhe baje tak helpdesk par call bhi kar sakte hain. Dhanyawwad"
    }
}

# =========================
# MODELS
# =========================

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    slots: dict
    hangup: bool

# =========================
# UTIL FUNCTIONS
# =========================

def secure_merge_slots(old, new, cannot_provide):
    """Merge slots but skip ones user cannot provide"""
    merged = old.copy()
    for k, v in new.items():
        if v not in (None, "", "null") and not cannot_provide.get(k, False):
            merged[k] = v
    return merged

def detect_program_level(course):
    """Detect if course is UG, PG, or PhD"""
    if not course:
        return "UG"

    course_lower = course.lower()

    # UG indicators
    ug_keywords = ["b.tech", "btech", "bca", "bba", "b.com", "bcom", "ba ", "bsc", "b.des", "bva", "llb"]
    if any(keyword in course_lower for keyword in ug_keywords):
        return "UG"

    # PG indicators
    pg_keywords = ["m.tech", "mtech", "mca", "mba", "llm", "ma ", "msc", "m.des", "mva", "m.com", "mcom"]
    if any(keyword in course_lower for keyword in pg_keywords):
        return "PG"

    # PhD
    if "phd" in course_lower:
        return "PhD"

    return "UG"  # Default

def determine_next_critical_slot(slots, cannot_provide):
    """Determine next critical slot to collect, respecting user constraints"""
    for key in CRITICAL_SLOTS:
        if not slots.get(key) and not cannot_provide.get(key, False):
            return key
    return None

def is_flow_complete(slots):
    """Check if minimum required information is collected"""
    name_filled = slots.get("Name") not in (None, "", "null")
    course_filled = slots.get("Course") not in (None, "", "null")
    city_filled = slots.get("City") not in (None, "", "null")

    # Flow is complete when Name + Course + City are filled
    return name_filled and course_filled and city_filled

def get_hangup_response(hangup_type, language):
    """Get appropriate hangup response based on type and language"""
    if hangup_type in HANGUP_RESPONSES:
        # Normalize language
        if language in ["Hindi", "Hinglish"]:
            return HANGUP_RESPONSES[hangup_type].get(language, HANGUP_RESPONSES[hangup_type]["English"])
        return HANGUP_RESPONSES[hangup_type]["English"]
    return None

# =========================
# LLM FUNCTIONS
# =========================

async def get_manager_decision(history, slots, user_msg):
    """Enhanced manager with conversation history context"""
    last_bot = "None"
    for h in reversed(history):
        if h["role"] == "assistant":
            last_bot = h["content"]
            break

    # Get recent conversation context
    conv_history = "\n".join(
        f"{h['role']}: {h['content']}" for h in history[-6:]
    ) or "None"

    prompt = MANAGER_SYSTEM_PROMPT.format(
        previous_slots=json.dumps(slots),
        last_bot_message=last_bot,
        conversation_history=conv_history
    )

    try:
        resp = await groq_client.chat.completions.create(
            model=MANAGER_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print("Manager Error:", e)
        return {}

async def rephrase_query(history, user_msg, query_count):
    """Rephrase query with query count tracking and hangup detection"""
    history_text = "\n".join(
        f"{h['role']}: {h['content']}" for h in history[-4:]
    ) or "None"

    prompt = QUERY_REPHRASER_PROMPT.format(
        conversation_history=history_text,
        user_message=user_msg,
        query_count=query_count
    )

    try:
        resp = await groq_client.chat.completions.create(
            model=MANAGER_MODEL,
            messages=[{"role": "system", "content": prompt}],
            temperature=0,
            max_tokens=512
        )
        rephrased = resp.choices[0].message.content.strip()
        print(f"Rephrased Query/Hangup: {rephrased}")
        return rephrased
    except Exception as e:
        print("Rephraser Error:", e)
        return user_msg

async def search_vector_db(query):
    if not query:
        return ""

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                VECTOR_DB_URL,
                params={"query": query},
                timeout=2
            )
            if resp.status_code == 200:
                result = resp.json()
                print(f"Vector DB Result: {result}")
                return result
            return ""
        except Exception as e:
            print("Vector DB Error:", e)
            return ""

def check_counselor_mentioned(history):
    """Check if counselor was already mentioned"""
    counselor_keywords = ["counselor will confirm", "counselor will reach", "counsellor", "counselors will"]

    for msg in history:
        if msg["role"] == "assistant":
            if any(keyword in msg["content"].lower() for keyword in counselor_keywords):
                return True
    return False

def check_facility_mentioned(history):
    """Check if facility was already mentioned"""
    facility_keywords = ["hostel facilities", "bus transport facilities", "hostel facility", "bus transport"]

    for msg in history:
        if msg["role"] == "assistant":
            if any(keyword in msg["content"].lower() for keyword in facility_keywords):
                return True
    return False

# =========================
# MAIN ENDPOINT
# =========================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user_id = request.user_id
    user_input = request.message

    hist_key = f"hist:{user_id}"
    slot_key = f"slots:{user_id}"
    cannot_provide_key = f"cannot_provide:{user_id}"
    query_count_key = f"query_count:{user_id}"

    raw_hist, raw_slots, raw_cannot, raw_query_count = await asyncio.gather(
        redis_conn.get(hist_key),
        redis_conn.get(slot_key),
        redis_conn.get(cannot_provide_key),
        redis_conn.get(query_count_key)
    )

    history = json.loads(raw_hist) if raw_hist else []
    slots = json.loads(raw_slots) if raw_slots else {k: None for k in CRITICAL_SLOTS + OPTIONAL_SLOTS}
    user_cannot_provide = json.loads(raw_cannot) if raw_cannot else {}
    query_count = int(raw_query_count) if raw_query_count else 0

    # Add initial greeting if this is the first message
    if not history:
        initial_greeting = "Good day! I am Riya, an admission counselor at J-E-C-R-C University. I would be happy to assist you with your admission queries. May I have your name, please?"
        history.append({"role": "assistant", "content": initial_greeting})

    # Increment query count
    query_count += 1

    # Get manager decision first to check for hangup conditions
    manager = await get_manager_decision(history, slots, user_input)
    
    # Get language for hangup responses
    language = manager.get("language", "English")

    # Update user_cannot_provide from manager BEFORE checking hangup
    new_cannot_provide = manager.get("user_cannot_provide", {})
    user_cannot_provide.update(new_cannot_provide)

    # Merge slots FIRST (to capture data even if hangup is triggered)
    slots = secure_merge_slots(slots, manager.get("extracted_slots", {}), user_cannot_provide)

    # Check for specific hangup types from manager
    hangup_type = manager.get("hangup_type")
    
    if hangup_type:
        # Get appropriate hangup response
        bot_msg = get_hangup_response(hangup_type, language)
        
        if bot_msg:
            history.extend([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": bot_msg}
            ])

            # Save state WITH UPDATED SLOTS
            await asyncio.gather(
                redis_conn.set(hist_key, json.dumps(history[-10:]), ex=3600),
                redis_conn.set(slot_key, json.dumps(slots), ex=3600),
                redis_conn.set(cannot_provide_key, json.dumps(user_cannot_provide), ex=3600),
                redis_conn.set(query_count_key, str(query_count), ex=3600)
            )

            return ChatResponse(response=bot_msg, slots=slots, hangup=True)

    # Check for counselor request hangup
    if manager.get("requesting_counselor_call", False) and manager.get("hangup_reason") == "counselor_requested":
        bot_msg = "I have documented your information. Our admission counselor will reach out to you at the earliest. Thank you for your interest in J-E-C-R-C University!"

        history.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": bot_msg}
        ])

        # Save state
        await asyncio.gather(
            redis_conn.set(hist_key, json.dumps(history[-10:]), ex=3600),
            redis_conn.set(slot_key, json.dumps(slots), ex=3600),
            redis_conn.set(cannot_provide_key, json.dumps(user_cannot_provide), ex=3600),
            redis_conn.set(query_count_key, str(query_count), ex=3600)
        )

        return ChatResponse(response=bot_msg, slots=slots, hangup=True)

    # Check for non-admission query hangup
    if manager.get("non_admission_query", False) and manager.get("hangup_reason") == "non_admission_intent":
        bot_msg = "I apologize, but I can only assist with admission queries related to J-E-C-R-C University. For other inquiries, please contact the appropriate department. Thank you for your understanding."

        history.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": bot_msg}
        ])

        # Save state
        await asyncio.gather(
            redis_conn.set(hist_key, json.dumps(history[-10:]), ex=3600),
            redis_conn.set(slot_key, json.dumps(slots), ex=3600),
            redis_conn.set(cannot_provide_key, json.dumps(user_cannot_provide), ex=3600),
            redis_conn.set(query_count_key, str(query_count), ex=3600)
        )

        return ChatResponse(response=bot_msg, slots=slots, hangup=True)

    # Get rephrased query or hangup detection
    vector_query = await rephrase_query(history, user_input, query_count)

    # Check for standard hangup (bye/thanks/done)
    is_hangup = "<hangup>" in vector_query.lower()

    if is_hangup:
        bot_msg = "Thank you for your time, Our counsellors will reach out to you soon!"

        history.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": bot_msg}
        ])

        # Save state
        await asyncio.gather(
            redis_conn.set(hist_key, json.dumps(history[-10:]), ex=3600),
            redis_conn.set(slot_key, json.dumps(slots), ex=3600),
            redis_conn.set(cannot_provide_key, json.dumps(user_cannot_provide), ex=3600),
            redis_conn.set(query_count_key, str(query_count), ex=3600)
        )

        return ChatResponse(response=bot_msg, slots=slots, hangup=True)

    # Detect program level
    program_level = manager.get("program_level") or detect_program_level(slots.get("Course"))

    # Determine next critical slot
    next_slot = determine_next_critical_slot(slots, user_cannot_provide)

    # Check if flow is complete
    flow_complete = is_flow_complete(slots)

    # Build dynamic instruction
    instruction = "Provide professional and informative responses to the user's inquiries."

    if not flow_complete and next_slot:
        # Still in collection phase
        if next_slot == "Name":
            instruction += " Subsequently, courteously request their name for personalized assistance."
        elif next_slot == "Course":
            instruction += " Then professionally inquire about their program of interest."
        elif next_slot == "Percentage":
            instruction += f" Subsequently request their {program_level} academic percentage for eligibility assessment."
        elif next_slot == "City":
            instruction += " Then request their city and state information for our records."
    else:
        # Flow complete - Q&A mode
        instruction += " Continue providing professional assistance without requesting previously collected information."

    # Get context from vector DB (only if not hangup)
    context_data = await search_vector_db(vector_query)

    # Check flags
    counselor_mentioned = check_counselor_mentioned(history)
    facility_mentioned = check_facility_mentioned(history)

    # Get user's name for personalization
    user_name = slots.get("Name") or "student"

    # Prepare persona prompt
    persona_prompt = RIYA_PERSONA_PROMPT.format(
        language=language,
        current_slots=json.dumps(slots),
        program_level=program_level,
        user_cannot_provide=json.dumps(user_cannot_provide),
        show_scholarship_alert=manager.get("is_scholarship_eligible", False),
        counselor_mentioned=counselor_mentioned,
        facility_mentioned=facility_mentioned,
        requesting_counselor_call=manager.get("requesting_counselor_call", False),
        context_data=context_data,
        name_filled=slots.get("Name") not in (None, "", "null"),
        course_filled=slots.get("Course") not in (None, "", "null"),
        minimal_info_collected=flow_complete,
        user_name=user_name,
        instruction=instruction
    )

    final = await groq_client.chat.completions.create(
        model=PERSONA_MODEL,
        messages=[
            {"role": "system", "content": persona_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.7,
        max_tokens=512
    )

    bot_msg = final.choices[0].message.content

    history.extend([
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": bot_msg}
    ])

    # Save state (keep last 10 messages to include initial greeting)
    await asyncio.gather(
        redis_conn.set(hist_key, json.dumps(history[-10:]), ex=3600),
        redis_conn.set(slot_key, json.dumps(slots), ex=3600),
        redis_conn.set(cannot_provide_key, json.dumps(user_cannot_provide), ex=3600),
        redis_conn.set(query_count_key, str(query_count), ex=3600)
    )

    print(bot_msg)

    return ChatResponse(response=bot_msg, slots=slots, hangup=False)

# =========================
# RUN
# =========================

def main():
    uvicorn.run(app, host="0.0.0.0", port=9001)

if __name__ == "__main__":
    main()