async def convert_google_drive_url_accesible_url(url : str) -> str : 

    file_id : str

    if '/file/d/' in url : file_id = url.split('/file/d')[1].split('/')[0]
    elif 'id=' in url : file_id = url.split('id=')[1].split('/')[0]
    else : raise ValueError(f'Not able to process google drive url : {url}')

    url = f'https://drive.google.com/uc?export=download&id={file_id}'

    return url