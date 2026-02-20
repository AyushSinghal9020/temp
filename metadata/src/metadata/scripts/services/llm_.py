import ast
from logging import Logger
import time
import traceback
from llm import GROQ_LLM 
import json

async def get_summary(
    groq_client : GROQ_LLM , 
    transcription : list[dict[str , str | int]] , 
    logger : Logger
) -> tuple[bool , str] : 

    try : 

        start_time : float = time.time()

        system_prompt : str = '''
            You are an expert at analyzing and summarizing audio transcriptions of conversations between the JECRC University AI Agent and a student or a parent.

            *** CRITICAL OUTPUT INSTRUCTIONS ***
            1. RAW HTML ONLY: Your entire response must consist strictly of valid HTML code.
            2. NO MARKDOWN: Do NOT use markdown code blocks (e.g., ```html or ```).
            3. NO TEXT: Do NOT provide any introductory phrases, explanations, or labels.
            4. START AND END: Start immediately with <p> and end immediately with </p>.
            5. ALLOWED TAGS: Use ONLY <p>, <b>, <ul>, and <li>. All other tags are PROHIBITED.

            Structure & Content:
            1. **Introduction:** Start with a single paragraph <p> that identifies the caller (transliterated name) and summarizes their main question or issue.
            2. **Details:** Follow with an unordered list <ul> containing list items <li> that cover the key discussion points and facts.
            3. **Conclusion:** End with a single paragraph <p> describing the final resolution or outcome of the conversation.

            **Language Rules:**
            - Write in proper English.
            - Transliterate all Hindi names/terms to English (e.g., "आरव" -> "Aarav").
            - You may use <b> only to highlight specific names or dates within the sentences, but do not use it for section headers.

            Example Output:
            <p>The parent, <b>Suresh</b>, contacted the support line to inquire about the hostel fee payment schedule for the <b>B.Tech</b> program.</p><ul><li>The AI Agent explained the installment options available for the current semester.</li><li>Deadlines for the first and second installments were clarified as being next Monday.</li></ul><p>The agent completed the call with a good gesture and the customer was satisfied</p>
        '''

        response : str = await groq_client(
            messages = await groq_client.create_messages(
                system_prompt = system_prompt , 
                user_input = f'Transcript : {str(transcription)}'
            ) , 
            model = 'openai/gpt-oss-120b'
        )

        logger.info(f'Summary time {time.time() - start_time}')

        return True , response 

    except Exception as e : 

        logger.error(f'Not able to summarise issue, {e} , {traceback.format_exc()}')

        return (False , 'Sorry we were not able to process this thing')

async def get_keywords(
    groq_client : GROQ_LLM , 
    transcription : list[dict[str , str | int]] , 
    summary : str , 
    logger : Logger
) -> tuple[bool , list[str]] : 

    try : 

        start_time : float = time.time()

        system_prompt : str = '''
            You are an expert at extracting structured metadata from audio transcriptions between a user (student/parent) and the JECRC University AI Agent.

            **Your Task:**
            Analyze the provided transcription and summary to generate a list of relevant tags. You must select tags ONLY from the "Allowed Inquiry Categories" list provided below. Do not invent, generalize, or create new tags.

            **Allowed Inquiry Categories (Strictly Choose From These):**
            {
                ADMISSIONS,
                FEE_STRUCTURE,
                HOSTEL_INQUIRY,
                SCHOLARSHIP,
                CAMPUS_VISIT,
                DOCUMENT_VERIFICATION,
                PLACEMENT_QUERY,
            }

            **Constraints:**
            - **Strict Selection:** Identify all categories mentioned in the conversation. If a specific category is not mentioned, do not include it.
            - **Variable Length:** 
                - If multiple topics are discussed (e.g., fees and hostel), return all applicable tags: `["Fee Structure", "Hostel Inquiry"]`
                - If only one topic is discussed, return a list with one string: `["Admissions"]`
                - If the transcription is empty, irrelevant, or contains none of the allowed values, return an empty list: `[]`
            - **Output Format:** Return only a Python-style list of strings. No preamble, no explanation, no supporting text.

            **Example Scenarios:**
            - *User asks about B.Tech fees:* `["Fee Structure"]`
            - *User asks about visiting the campus and scholarship options:* `["Campus Visit", "Scholarship"]`
            - *User asks about hostel facilities:* `["Hostel Inquiry"]`
            - *User asks about something not in the list (e.g., faculty names):* `[]`
        '''

        response : str = await groq_client(
            messages = await groq_client.create_messages(
                system_prompt = system_prompt , 
                user_input = f'''
                    Transcript : {str(transcription)}

                    Summary : {summary}
                '''
            ) , 
            model = 'openai/gpt-oss-120b'
        )

        response = response.replace('`' , '').replace('python' , '').replace('json' , '').replace('- ' , '')

        list_response : list = ast.literal_eval(response)

        logger.info(f'Keywords time : {time.time() - start_time}')

        return True , list_response

    except Exception as e : 

        logger.error(f'Not able to keyword issue, {e} , {traceback.format_exc()}')

        return (False , [])

async def analyze_sentiment(
    groq_client : GROQ_LLM , 
    transcription : list[dict[str , str | int]] , 
    summary : str , 
    logger : Logger
) -> tuple[bool , dict[str , float]] : 

    try : 

        start_time : float = time.time()

        system_prompt : str = '''
            **Role:**  
            You are the **Lead Quality Assurance Auditor** for JECRC University's AI Support Agent. Your sole purpose is to evaluate the quality of a conversation between the AI Agent and a student/parent (User).

            **Objective:**  
            Analyze the provided interaction transcript and generate a single satisfaction score between `0.0` and `1.0` based on strict performance metrics.

            **Input:**  
            A text transcript of a conversation between `[User]` and `[AI Agent]`.

            **Output Format:**  
            You must return **ONLY** a raw JSON object.  
            Do not include markdown formatting (like ```json ... ```), explanations, or preamble.  
            **Strict Output Schema:**  
            `{"score": <float>}`

            ---

            ## Scoring Logic & Weights

            Calculate the final score based on the following weighted criteria. Start with a baseline of **0.0** and add points based on performance.

            ### 1. Relevance & Understanding (Weight: 0.40)
            *   **Perfect (0.40):** The AI understood the intent immediately and provided a direct, accurate answer regarding JECRC University (e.g., specific admission dates, fee structures, campus facilities).
            *   **Partial (0.20):** The AI gave a generic answer or required the user to rephrase significantly to get the right information.
            *   **Failure (0.0):** The AI hallucinated information, answered a completely different question, or provided factually incorrect details about the university.

            ### 2. User Satisfaction & Sentiment (Weight: 0.40)
            *   **High (0.40):** The user explicitly expressed gratitude (e.g., "Thank you," "That helps," "Great") or relief.
            *   **Neutral (0.20):** The user acknowledged the answer but showed no strong emotion.
            *   **Negative (0.0):** The user expressed frustration, repeated the same question in anger, or explicitly stated the AI was unhelpful.

            ### 3. Logical Flow & Completion (Weight: 0.20)
            *   **Completed (0.20):** The conversation had a natural conclusion (e.g., "Is there anything else?", "Goodbye"). The loop was closed.
            *   **Abrupt (0.0):** The conversation ended while the user clearly still had a pending query, or the AI stopped responding in the middle of a thought.

            ## Penalties (Fatal Errors)
            If any of the following occur, override the calculation and cap the maximum score at **0.1**:
            1.  **AI Rudeness:** The Agent was polite, dismissive, or argumentative.
            2.  **System Loop:** The AI repeated the exact same phrase 3+ times.
            3.  **Refusal to Assist:** The AI refused to answer a basic query within its scope (e.g., "I cannot answer about fees").

            ---

            ## Examples

            **Example 1:**
            *Transcript:*
            User: What is the fee for B.Tech CSE?
            AI: The tuition fee for B.Tech CSE at JECRC University is approximately 1.6 Lakhs per annum.
            User: Okay, and is there a hostel?
            AI: Yes, we have on-campus hostels for both boys and girls.
            User: Perfect, thanks!
            AI: You're welcome! Let us know if you need anything else. Goodbye.

            *Output:*
            {"score": 1.0}

            **Example 2:**
            *Transcript:*
            User: Where is the campus located?
            AI: I am an AI model.
            User: I know, but where is JECRC?
            AI: JECRC is a university.
            User: You are useless.

            *Output:*
            {"score": 0.1}

            **Example 3:**
            *Transcript:*
            User: When do exams start?
            AI: Exams usually start in May.
            User: Okay.

            *Output:*
            {"score": 0.7} 
            *(Reasoning: Relevance is high, Satisfaction is neutral, Completion is abrupt/missing closing formalities).*

            ---

            **FINAL INSTRUCTION:**  
            Read the input conversation below. Evaluate strictly. Return ONLY the JSON string.
        '''

        response : str = await groq_client(
            messages = await groq_client.create_messages(
                system_prompt = system_prompt , 
                user_input = f'''
                    Transcript : {str(transcription)}

                    Summary : {summary}
                '''
            ) , 
            model = 'openai/gpt-oss-120b'
        )

        response = response.replace('`' , '').replace('python' , '').replace('json' , '').replace('- ' , '')

        dict_response : dict = ast.literal_eval(response)

        logger.info(f'Keywords time : {time.time() - start_time}')

        return True , dict_response

    except Exception as e : 

        logger.error(f'Not able to sentiment issue, {e} , {traceback.format_exc()}')

        return (False , {'score' : 0.5})

async def get_student_details(
    groq_client : GROQ_LLM , 
    transcription : list[dict[str , str | int]] , 
    summary : str , 
    logger : Logger
) -> tuple[bool , dict] : 

    try : 

        start_time : float = time.time()

        system_prompt : str = '''
**Role:** 
You are a specialized Data Extraction Engine. Your task is to analyze a provided **Transcription** and **Summary** of a student interaction and convert the relevant details into a strictly formatted JSON object.

**Input Context:**
1. A Transcription of a conversation.
2. A Summary of that conversation.

**Extraction Rules & Logic:**

1.  **name**: (String) The full name of the student. Use `null` if not mentioned.
2.  **score**: (Float) 
    *   **Source:** Extract the score of the most recent academic level completed (e.g., 12th marks, Bachelors, or masters). 
    *   **Priority:** If multiple scores are mentioned (e.g., 10th and 12th), prioritize the higher academic level (12th).
    *   **Formatting:** 
        *   Percentage (e.g., 85%): Represent as `85.0`.
        *   CGPA (e.g., 8.5): Multiply by 10 (e.g., `85.0`).
    *   **Default:** If no numeric score is mentioned for any level, set this value to `0.0`.
3.  **result_status**: (String) 
    *   Set to `"DECLARED"` if the student provides a specific score for their qualifying exam.
    *   Set to `"AWAITED"` if the student mentions they are currently appearing for exams or waiting for results.
    *   Must be exactly one of: `"DECLARED"` or `"AWAITED"`.
4.  **city**: (String) The student's current city of residence.
5.  **hostel**: (Boolean) `true` if the student requires or mentions interest in hostel facilities; `false` otherwise.
6.  **transport**: (Boolean) `true` if the student requires or mentions a bus/transport service; `false` otherwise.
9.  **course_code**: (String) 
    *   **Primary Intent Rule:** If the student discusses multiple levels (e.g., inquiring about PG while mentioning their UG background), you must identify the **Target Program** they wish to enroll in. 
    *   **No Mixing:** You MUST NOT combine parts from different levels (e.g., do not combine a PG school with a UG specialization). The code must exist as a valid path within one single branch of the hierarchy.
    *   **Format:** `<LEVEL>-<SCHOOL>-<PROGRAM>-<SPECIALIZATION>`
    *   **Logic:** 
        *   If "CSE" is mentioned for B.Tech, use `UG-SET-BTECH-CSE`.
        *   Do NOT invent codes. Use only the keys provided in the hierarchy.

**Course Hierarchy Ground Truth:**


            **Course Hierarchy Ground Truth:**
            ```yaml
            UG:
                SET:
                    label: School of Engineering and Technology
                    programs:
                    BTECH:
                        label: Bachelor of Technology
                        specializations:
                            CSE: Computer Science and Engineering
                            AI_DS: "CSE: Artificial Intelligence & Data Science"
                            CLOUD_MS: Cloud Computing (Microsoft)
                            CLOUD_AWS: Cloud Computing (Amazon-AWS)
                            AIML_XEBIA: Artificial Intelligence and Machine Learning (Xebia)
                            AIML_IBM: Artificial Intelligence and Machine Learning (IBM)
                            AIML_SAMATRIX: Artificial Intelligence and Machine Learning (Samatrix)
                            FSD_XEBIA: Full Stack Web Design and Development (Xebia)
                            CYBER_EC: "Cyber Security (EC Council, USA)"
                            DS_DA_SAMATRIX: Data Science & Data Analytic (Samatrix)
                            CSBS_TCS: Computer Science and Business Systems (TCS)
                            GEN_AI_LT: Generative AI (L&T EduTech)
                            GAMING: CSE in Gaming Technology
                            AI_DEVOPS: CSE in AI DevOps & Cloud Automation
                            SPE_KALVIUM: CSE with Specialization in Software Product Engineering (Kalvium)
                            CIVIL_LT: Civil Engineering with L&T EduTech
                            ECE_LT: Electronics & Communication Engineering With L&T EduTech
                            ECE_SEMI: Electronics & Comm. Eng. Specialization in Semiconductor & Chip Design
                            ME_LT: Mechanical Engineering with L&T EduTech
                            ME_EV: Mechanical Engineering with Specialization in Electric Vehicles
                    BTECH_LE:
                        label: B.Tech. Lateral Entry
                        specializations:
                            CSE: Computer Science and Engineering
                            CIVIL: Civil Engineering
                            ECE: Electronics and Communication Engineering
                            MECH: Mechanical Engineering
                SCA:
                    label: School of Computer Applications
                    programs:
                    BCA:
                        label: Bachelor of Computer Applications
                        specializations:
                            GEN: Bachelor of Computer Applications
                            AI_DS: Artificial Intelligence and Data Science
                            HEALTH: Health Informatics
                            AI_DEVOPS: AI DevOps & Cloud Automation
                    BCA_IND:
                        label: BCA Industry Specialization
                        specializations:
                            CYBER_EC: "Cyber Security (EC Council, USA)"
                            DS_SAMATRIX: Data Science & Data Analytics (Samatrix)
                            CLOUD_IBM: Cloud Computing & Full Stack Development (IBM)
                            AIML_IBM: Artificial Intelligence & Machine Learning (IBM)
                            CLOUD_AWS: Cloud Computing (Amazon-AWS)
                            FSD_XEBIA: Full Stack Web Design and Development (Xebia)
                JSB:
                    label: Jaipur School of Business
                    programs:
                    BBA:
                        label: Bachelor of Business Administration
                        specializations:
                            GEN: Bachelor of Business Administration
                            BFSI: Banking Finance Service & Insurance
                            DIGI_MKT: New Age Digital Marketing
                    BBA_IND:
                        label: BBA Industry Specialization
                        specializations:
                            DATA_SAMATRIX: Data Analytics & Data Visualization (Samatrix)
                    BCOM:
                        label: Bachelor of Commerce
                        specializations:
                            GEN: Bachelor of Commerce
                            CAPITAL: B.Com (Capital Market)
                SOL:
                    label: School of Law
                    programs.INT_LAW:
                    label: Integrated Law (5 Years)
                    specializations:
                        BA_LLB: B.A. LL.B. (Hons.)
                        BSC_LLB: B.Sc. LL.B. (Hons.)
                        BBA_LLB: BBA LL.B. (Hons.)
                JSE:
                    label: Jaipur School of Economics
                    programs.BA_HONS_ECO:
                    label: BA (Hons.) Economics
                    specializations:
                        ECO: Economics
                SOS:
                    label: School of Sciences
                    programs.BSC_HONS:
                    label: Bachelor of Science (Hons.)
                    specializations:
                        MICRO: Microbiology
                        BIOTECH: Biotechnology
                        FORENSIC: Forensic Science
                JSD:
                    label: Jaipur School of Design
                    programs:
                    BDES:
                        label: Bachelor of Design
                        specializations:
                            INTERIOR: Interior Design
                            JEWELLERY: Jewellery Design & Manufacturing Design
                            FASHION: Fashion Design
                    BVA:
                        label: Bachelor of Visual Arts
                        specializations:
                            GRAPHIC: Graphic Design
                            PAINTING: Painting Design
                SHSS:
                    label: School of Humanities and Social Sciences
                    programs:
                    BA_HONS:
                        label: Bachelor of Arts (Hons.)
                        specializations:
                            ENGLISH: English
                            PSYCH: Psychology
                            POLSCI: Political Science
                            PUBPOL: Public policy and Governance
                    BA_LIB:
                        label: Bachelor of Arts
                        specializations:
                            LIBERAL: Liberal Studies
                SOH:
                    label: School of Hospitality
                    programs.BSC_HHM:
                    label: B.Sc. in Hospitality and Hotel Management
                    specializations:
                        HHM: Hospitality and Hotel Management
                JSMC:
                    label: Jaipur School of Mass Communication
                    programs.BA_JMC:
                    label: Bachelor of Arts in Journalism & Mass Communication
                    specializations:
                        JMC: Journalism & Mass Communication
                KPART:
                    label: Programs with Knowledge Partners
                    programs:
                    BCOM_ISDC:
                        label: B.Com with ISDC
                        specializations:
                            ACCA: International Finance & Accounting (ACCA)
                            IOA: Finance & Analytics (IoA)
                            CMA: Management Accounting (CMA)
                            IFM: Financial Markets (IFM)
                            CIPS: Logistics (CIPS)
                    BBA_ISDC:
                        label: BBA with ISDC
                        specializations:
                            CIMA: Finance & Leadership (CIMA)
                            IFM: Financial Markets (IFM)
                            AI_SOC: Digital Business (AI Society)
                            IOA: Business Analytics (IOA)
                            DMI: Digital Marketing (DMI)
                            CIPS: Logistics (CIPS)
                    GB_ISDC:
                        label: Global Business (ISDC)
                        specializations:
                            INTL: International Program
                    BDES_ISDC:
                        label: B.Des with ISDC
                        specializations: 
                            COMM: Communication Design - World Design
                    BBA_CD:
                        label: BBA with College Dekho
                        specializations:
                            SALES: New Age Sales & Marketing
                            BRAND: Brand Management
                            HEALTH: Healthcare Management
                    BCA_CD:
                        label: BCA with College Dekho
                        specializations:
                            MERN: MERN Full Stack
                            RPA: Robotic Process Automation
                            FORENSIC: Digital Forensics
                            GAME: Game Development
                    BBA_SS:
                        label: BBA with Sunstone
                        specializations:
                            GEN: BBA (Sunstone)
            PG:
                SET:
                    label: School of Engineering and Technology
                    programs.MTECH:
                    label: Master of Technology
                    specializations:
                        STRUCT: Structural Engineering
                        TRANSPO: Transportation Engineering
                        ENV: Environmental Engineering
                        CONST: Construction Engg & Mgmt
                        AI: Artificial Intelligence (CSE)
                        CSE: Computer Science and Engineering
                        DATA: Data Analytics (CSE)
                        CYBER: Cyber Security (CSE)
                        CLOUD: Cloud Computing (CSE)
                        VLSI: VLSI & Embedded Systems (ECE)
                        DIGI_COMM: Digital Communication (ECE)
                        CAD_CAM: CAD/CAM (ME)
                        THERMAL: Thermal Engineering (ME)
                        PROD: Production Engineering (ME)
                        DESIGN: Design Engineering (ME)
                        EV: EV Engineering (Electrical)
                        RENEW: Renewable Energy (Electrical)
                        POWER: Power System and Automation (Electrical)
                SCA:
                    label: School of Computer Applications
                    programs:
                    MCA:
                        label: Master of Computer Applications
                        specializations:
                            GEN: Master of Computer Applications
                            AI_DS: Artificial Intelligence and Data Science
                    MCA_IND:
                        label: MCA Industry Specialization
                        specializations:
                            CYBER_EC: "Cyber Security (EC Council, USA)"
                            AIML_SAMATRIX: Artificial Intelligence & Machine Learning (Samatrix)
                            DS_SAMATRIX: Data Science & Data Analytics (Samatrix)
                            CLOUD_IBM: Cloud Computing & Full Stack Development (IBM)
                            CLOUD_AWS: Cloud Computing (Amazon-AWS)
                JSB:
                    label: Jaipur School of Business
                    programs:
                    MBA:
                        label: Master of Business Administration
                        specializations:
                            HR: Human Resource Management
                            MKT: Marketing Management
                            FIN: Finance Management
                            IT: Information Technology Management
                            OPS: Production & Operation Management
                            RETAIL: Retail Management
                            ENTRE: Entrepreneurship and Family Business Management
                            SOCIAL: Social Entrepreneurship
                            BFSI: Banking Finance Service & Insurance
                    MBA_IND:
                        label: MBA Industry Specialization
                        specializations:
                            DATA_SAMATRIX: Data Analytics & Data Visualization (Samatrix)
                            AI_SAMATRIX: Artificial Intelligence (Samatrix)
                SOL:
                    label: School of Law
                    programs.LLM:
                    label: Master of Laws
                    specializations:
                        GEN: LL.M
                JSE:
                    label: Jaipur School of Economics
                    programs.MA_ECO:
                    label: MA Economics
                    specializations:
                        ECO: Economics
                SAHS:
                    label: School of Allied Health Sciences
                    programs.MSC_SAHS:
                    label: M.Sc. Clinical Embryology
                    specializations:
                        EMBRYO: Clinical Embryology in Association with Indira IVF
                SOS:
                    label: School of Sciences
                    programs.MSC_SOS:
                    label: Master of Science
                    specializations:
                        MICRO: Microbiology
                        BIOTECH: Biotechnology
                        FORENSIC: Forensic Science
                        MAT_CHEM: Material Chemistry
                        DIGI_FORENSIC: Digital Forensics
                        PHY: Physics
                        CHEM: Chemistry
                        MATH: Mathematics
                        BOTANY: Botany
                        ZOOLOGY: Zoology
                JSD:
                    label: Jaipur School of Design
                    programs:
                    MDES:
                        label: Masters of Design
                        specializations:
                            INTERIOR: Interior Design
                            FASHION: Fashion Design
                    MVA:
                        label: Masters of Visual Arts
                        specializations:
                            GRAPHIC: Graphic Design
                    MSC_DES:
                        label: M.Sc. Design
                        specializations:
                            INT_JEWEL: Interior / Jewellery Design
                            FASHION: Fashion Design
                SHSS:
                    label: School of Humanities and Social Sciences
                    programs.MA_SHSS:
                    label: Master of Arts
                    specializations:
                        ENGLISH: English
                        IR: International Relations
                        PSYCH: Psychology
                        POLSCI: Political Science
                JSMC:
                    label: Jaipur School of Mass Communication
                    programs.MA_JMC:
                    label: Master of Arts in Journalism & Mass Communication
                    specializations:
                        JMC: Journalism & Mass Communication
                KPART:
                    label: Programs with Knowledge Partners
                    programs:
                    MBA_ISDC:
                        label: MBA with ISDC
                        specializations:
                            ACCA: International Finance (ACCA)
                            CIMA: Finance & Leadership (CIMA)
                            DIGI: Digital Business
                            ANALYTICS: Analytics
                            MARKETS: Markets
                            MKT: Marketing
                            LOGISTICS: Logistics
                    MCOM_ISDC:
                        label: M.Com with ISDC
                        specializations:
                            INTL_FIN: International Finance & Accounting
                            MGMT_ACCT: Management Accounting
                    MBA_CD:
                        label: MBA with College Dekho
                        specializations:
                            FIN_OPS: Global Financial Operations
                            HR: Applied HR
                            SALES: New Age Sales & Marketing
                            PROD: Product Mgmt
                            BRAND: Brand Mgmt
                            HEALTH: Healthcare Mgmt
                            INV_BANK: Investment Banking
                    MCA_CD:
                        label: MCA with College Dekho
                        specializations:
                            MERN: MERN Full Stack
                    MBA_SS:
                        label: MBA with Sunstone
                        specializations:
                            GEN: MBA (Sunstone)
                    MBA_IM:
                        label: MBA with Imarticus
                        specializations:
                            FINTECH: Fintech
            PHD.RES:
                label: Doctoral Program (Ph.D.)
                programs:
                    PHD:
                    label: Doctor of Philosophy
                    specializations:
                        ENG: Engineering
                        MGMT: Management
                        COMM: Commerce
                        HOTEL: Hotel Mgmt
                        JMC: Journalism
                        SCI: Sciences
                        LAW: Law
                        DES: Design
                        ENGLISH: English
                        ECO: Economics
                        PSYCH: Psychology
            **Constraint Guidelines:**
            - If a value is missing and no default is specified, use `null`.
            - **Output Format:** Return ONLY the JSON object. Do not include introductory text, explanations, or markdown formatting outside the JSON block.
            - Ensure all numeric values are `float` and all boolean values are `true/false`.

            **Expected JSON Structure:**
            ```json
            {
                "name": string or null,
                "score": float,
                "result_status": "DECLARED" | "AWAITED",
                "city": string or null,
                "hostel": boolean,
                "transport": boolean,
                "course_code": string or null
            }
            ```
        '''

        response : str = await groq_client(
            messages = await groq_client.create_messages(
                system_prompt = system_prompt , 
                user_input = f'''
                    Transcript : {str(transcription)}

                    Summary : {summary}
                '''
            ) , 
            model = 'meta-llama/llama-4-scout-17b-16e-instruct'
        )

        response = response.replace('`' , '').replace('python' , '').replace('json' , '').replace('- ' , '')

        list_response : dict = json.loads(response)

        logger.info(f'Keywords time : {time.time() - start_time}')

        return True , list_response

    except Exception as e : 

        logger.error(f'Not able to keyword issue, {e} , {traceback.format_exc()}')

        return (False , {})
