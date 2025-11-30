"""
配置管理
"""

import os 
import yaml 
from pathlib import Path 
from dataclasses import dataclass 
from typing import Dict ,Any ,Optional 
from dotenv import load_dotenv 


project_root =Path (__file__ ).parent .parent .parent .parent 
load_dotenv (project_root /'.env')


@dataclass 
class FeishuConfig :

    app_id :str 
    app_secret :str 


@dataclass 
class WebhookConfig :

    port :int =8080 
    host :str ="0.0.0.0"


@dataclass 
class SessionConf :

    storage_file :str ="data/sessions.json"
    token_length :int =8 
    expiration_hours :int =24 
    cleanup_interval_minutes :int =60 


@dataclass 
class LoggingConfig :

    level :str ="INFO"
    file :str ="data/logs/app.log"
    format :str ="%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass 
class CardsConfig :

    task_completed_card_id :str =""
    task_waiting_card_id :str =""
    command_result_card_id :str =""
    session_list_card_id :str =""


@dataclass 
class SecurityConfig :

    whitelist_file :str ="configs/security/whitelist.yaml"
    max_command_length :int =1000 
    dangerous_commands :list =None 


class Config :


    def __init__ (self ):
        self .feishu :Optional [FeishuConfig ]=None 
        self .webhook :WebhookConfig =WebhookConfig ()
        self .session :SessionConf =SessionConf ()
        self .logging :LoggingConfig =LoggingConfig ()
        self .cards :CardsConfig =CardsConfig ()
        self .security :SecurityConfig =SecurityConfig ()

    @classmethod 
    def load_from_file (cls ,config_path :str ="configs/config.yaml")->'Config':

        config =cls ()


        if Path (config_path ).exists ():
            with open (config_path ,'r',encoding ='utf-8')as f :
                data =yaml .safe_load (f )or {}


            if 'feishu'in data :
                config .feishu =FeishuConfig (
                app_id =cls ._resolve_env (data ['feishu'].get ('app_id','')),
                app_secret =cls ._resolve_env (data ['feishu'].get ('app_secret',''))
                )

            if 'webhook'in data :
                config .webhook =WebhookConfig (**data ['webhook'])

            if 'session'in data :
                config .session =SessionConf (**data ['session'])

            if 'logging'in data :
                config .logging =LoggingConfig (**data ['logging'])

            if 'cards'in data :
                config .cards =CardsConfig (**data ['cards'])

            if 'security'in data :
                config .security =SecurityConfig (**data ['security'])


        config ._load_from_env ()

        return config 

    def _load_from_env (self ):


        app_id =os .getenv ('FEISHU_APP_ID')
        app_secret =os .getenv ('FEISHU_APP_SECRET')
        if app_id and app_secret :
            self .feishu =FeishuConfig (app_id =app_id ,app_secret =app_secret )


        if os .getenv ('WEBHOOK_PORT'):
            self .webhook .port =int (os .getenv ('WEBHOOK_PORT'))


        if os .getenv ('SESSION_STORAGE_FILE'):
            self .session .storage_file =os .getenv ('SESSION_STORAGE_FILE')


        if os .getenv ('LOG_LEVEL'):
            self .logging .level =os .getenv ('LOG_LEVEL')

    @staticmethod 
    def _resolve_env (value :str )->str :

        if isinstance (value ,str )and value .startswith ('${')and value .endswith ('}'):
            env_var =value [2 :-1 ]
            return os .getenv (env_var ,value )
        return value 



_config_instance :Optional [Config ]=None 


def get_config ()->Config :

    global _config_instance 
    if _config_instance is None :
        _config_instance =Config .load_from_file ()
    return _config_instance 
