import json
import yaml
import itertools
from llm import GROQ_LLM
# from llm.src.llm import GROQ_LLM
from tqdm import tqdm

from dotenv import load_dotenv

load_dotenv('../../.env')

def generate_scenarios(config : dict) : 

    llm_client : GROQ_LLM = GROQ_LLM(config['groq'])

    with open(config['path']) as system_prompt_file : 
        system_prompt : str = system_prompt_file.read()

    with open(config['course-details']) as course_file : 
        course_data : dict = json.load(course_file)


    courses = list(course_data.keys())

    permutations = list(itertools.product(courses , config['languages'] , config['emotions'] , config['scopes'] , config['lengths']))

    if config['take-every'] != 'all' : 
        permutations = [permutations[index] for index in range(0 , len(permutations) , config['take-every'])]

    if config['limit'] != 'no-limit' : 
        permutations = permutations[: config['limit']]

    results = []

    with tqdm(total = len(permutations) , desc = "Total Progress") as pbar : 

        for course , lang , emotion , scope , length in permutations : 

            course_fee = course_data[course]

            formatted_prompt = system_prompt.replace(
                '{course_name}' , str(course)
            ).replace(
                '{fee}' , str(course_fee)
            ).replace(
                '{language}' , str(lang) 
            ).replace(
                '{emotion}' , str(emotion)
            ).replace(
                '{scope}' , str(scope)
            ).replace(
                '{length}' , str(length)
            )

            response : dict = llm_client.run_model_json(messages = [
                {
                    'role' : 'system' , 
                    'content' : formatted_prompt
                } , 
                {
                    'role' : 'user' , 
                    'content' : 'Generate the conversation'
                }
            ])

            scenario_entry = {
                'tags' : {
                    'course' : course , 
                    'language' : lang , 
                    'emotion' : emotion , 
                    'scope' : scope , 
                    'length' : length
                } , 
                'conversation' : response['conversation']
            }
            
            results.append(scenario_entry)
            
            pbar.update(1)

    return results

def main() : 

    with open('config.yml') as config_file : 
        config : dict = yaml.safe_load(config_file)

    scenarios : list = generate_scenarios(config)

    # print(json.dumps(scenarios , indent = 4))
    

    with open('assets/jecrc_scenarios.json' , 'w') as file : 
        json.dump(scenarios , file , indent = 4)