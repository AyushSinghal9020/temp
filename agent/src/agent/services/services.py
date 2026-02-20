import json
from redis.client import Redis


async def load_data_with_key(key : str , redis_client : Redis) -> str : 

    return await redis_client.get(key)

async def get_user_data(
    user_id : str , 
    redis_client
) : 

    user_data = await load_data_with_key(user_id , redis_client)

    if user_data : 
        return json.loads(user_data)

    else : 
        return {
            'history' : [] , 
            'slots' : {} , 
            'cannot_provide_key' : {} , 
            'query_count_key' : 0 , 
            'awaiting_form_confirmation' : False
        }

async def set_user_data(
    user_id : str , 
    redis_client ,
    data : dict 
) -> None : 

    await redis_client.set(user_id , json.dumps(data))

def secure_merge_slots(old , new , cannot_provide) : 

    merged = old.copy()

    for key , value in new.items() : 

        if (
            value not in (None , "" , "null") and 
            not cannot_provide.get(key , False)
        ) : 
            merged[key] = value

    return merged


def detect_program_level(course : str , config : dict) -> str : 

    if not course : 
        return 'UG'

    course_lower = course.lower()

    ug_keywords = ['b.tech', 'btech', 'bca', 'bba', 'b.com', 'bcom', 'ba ', 'bsc', 'b.des', 'bva', 'llb']
    if any(keyword in course_lower for keyword in ug_keywords) : 
        return 'UG'

    pg_keywords = ['m.tech', 'mtech', 'mca', 'mba', 'llm', 'ma ', 'msc', 'm.des', 'mva', 'm.com', 'mcom']
    if any(keyword in course_lower for keyword in pg_keywords) : 
        return 'PG'

    if 'phd' in course_lower : 
        return 'PhD'

    return 'UG'

def needs_stream_verification(course) : 

    if not course:
        return False
    
    course_lower = course.lower()

    return any(keyword in course_lower for keyword in ["b.tech", "btech", "mca", "bsc"])

def determine_next_critical_slot(slots , config) : 

    for key in config['next-critical-slots'] : 

        if not slots.get(key) : 
            return key

    return None

def is_flow_complete(slots) -> bool : 

    name_filled = slots.get('Name') not in (None , '' , 'null')
    course_filled = slots.get('Course') not in (None , '' , 'null')
    city_filled = slots.get('City') not in (None , '' , 'null')

    return name_filled and course_filled and city_filled

def check_gap_year(passing_year):
    """Check if passing year indicates a gap year (2023 or earlier = 3+ years)"""
    if not passing_year:
        return False
    
    try:
        year = int(passing_year)
        current_year = 2026
        return year <= 2023  # 3 or more years gap
    except:
        return False

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

def check_stream_asked(history):
    """Check if stream/subjects question was already asked"""
    stream_keywords = ["physics, chemistry, and mathematics", "p-c-m", "pcm", "b-c-a in your graduation"]

    for msg in history:
        if msg["role"] == "assistant":
            if any(keyword in msg["content"].lower() for keyword in stream_keywords):
                return True
    return False
