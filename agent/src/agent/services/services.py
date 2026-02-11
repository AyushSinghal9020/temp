def _parse_list(value : str) -> list : 

    if value == '*' : return ['*']

    return [x.strip() for x in value.split(',')]

def _parse_bool(value : str) -> bool : return value.lower() == 'true'

def env_str_to_list(
    value : str ,  
    default : str = '*'
) -> list : 

    if not value : value = default
    return _parse_list(value)

def env_str_to_bool(
    value : str , 
    default : str = 'True'
) -> bool : 

    if not value : value = default
    return _parse_bool(value)