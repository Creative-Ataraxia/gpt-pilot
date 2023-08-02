from helpers.Agent import Agent
import json
from termcolor import colored
from helpers.AgentConvo import AgentConvo

from logger.logger import logger
from database.database import save_progress, save_app, get_progress_steps
from utils.utils import execute_step, generate_app_data, step_already_finished
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, get_additional_info_from_openai, \
    generate_messages_from_description, get_additional_info_from_user
from const.function_calls import USER_STORIES, USER_TASKS

class ProductOwner(Agent):
    def __init__(self, project):
        super().__init__('product_owner', project)

    def get_project_description(self):
        self.project.current_step = 'project_description'
        convo_project_description = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return step['summary'], step['messages']

        # PROJECT DESCRIPTION
        self.project.args['app_type'] = ask_for_app_type()

        save_app(self.project.args['user_id'], self.project.args['app_id'], self.project.args['app_type'])

        main_prompt = ask_for_main_app_definition()

        high_level_messages = get_additional_info_from_openai(
            generate_messages_from_description(main_prompt, self.project.args['app_type']))

        high_level_summary = convo_project_description.send_message('utils/summary.prompt',
                                                {'conversation': '\n'.join(
                                                    [f"{msg['role']}: {msg['content']}" for msg in high_level_messages])})

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "prompt": main_prompt,
            "messages": high_level_messages,
            "summary": high_level_summary,
            "app_data": generate_app_data(self.project.args)
        })

        self.project_description = high_level_summary
        return high_level_summary
        # PROJECT DESCRIPTION END


    def get_user_stories(self):
        self.project.current_step = 'user_stories'
        self.convo_user_stories = AgentConvo(self)
        
        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return step['user_stories'], step['messages']

        # USER STORIES
        print(colored(f"Generating user stories...\n", "green"))
        logger.info(f"Generating user stories...")

        user_stories = self.convo_user_stories.send_message('user_stories/specs.prompt', {
            'prompt': self.project_description,
            'app_type': self.project.args['app_type']
        }, USER_STORIES)

        logger.info(user_stories)
        user_stories = get_additional_info_from_user(user_stories, 'product_owner')

        logger.info(f"Final user stories: {user_stories}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_user_stories.messages,
            "user_stories": user_stories,
            "app_data": generate_app_data(self.project.args)
        })

        return user_stories
        # USER STORIES END


    def get_user_tasks(self):
        current_step = 'user_tasks'

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], current_step)
        if step and not execute_step(self.project.args['step'], current_step):
            step_already_finished(self.project.args, step)
            return step['user_tasks']

        # USER TASKS
        print(colored(f"Generating user tasks...\n", "green"))
        logger.info(f"Generating user tasks...")

        user_tasks = self.convo_user_stories.send_message('user_stories/user_tasks.prompt',
                                        {}, USER_TASKS)

        logger.info(user_tasks)
        user_tasks = get_additional_info_from_user(user_tasks, 'product_owner')

        logger.info(f"Final user tasks: {user_tasks}")

        save_progress(self.project.args['app_id'], current_step, {
            "messages": self.convo_user_stories.messages,
            "user_tasks": user_tasks,
            "app_data": generate_app_data(self.project.args)
        })

        return user_tasks
        # USER TASKS END