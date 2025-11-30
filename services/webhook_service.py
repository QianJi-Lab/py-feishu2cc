"""
Webhook 服务入口
"""

import os 
import sys 
import logging 
from pathlib import Path 
from dotenv import load_dotenv 


project_root =Path (__file__ ).parent .parent 


load_dotenv (project_root /'.env')


sys .path .insert (0 ,str (project_root /'src'))

from fastapi import FastAPI ,HTTPException ,Request 
from fastapi .responses import JSONResponse 
import uvicorn 
import json 
import re 

from feishu_bot .session import SessionManager ,SessionConfig 
from feishu_bot .config import get_config 
from feishu_bot .security import UserMappingService 
from feishu_bot .bot import FeishuClient 
from feishu_bot .notification import (
WebhookRequest ,
WebhookResponse ,
NotificationSender ,
WebhookHandler 
)


logging .basicConfig (
level =logging .INFO ,
format ='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger =logging .getLogger (__name__ )


config =get_config ()


session_manager =SessionManager (
config .session .storage_file ,
SessionConfig (
token_length =config .session .token_length ,
expiration_hours =config .session .expiration_hours ,
cleanup_interval_minutes =config .session .cleanup_interval_minutes 
)
)


try :
    user_mapping_service =UserMappingService (config .security .whitelist_file )
except Exception as e :
    logger .warning (f"Failed to load user mapping service: {e }")
    user_mapping_service =None 


if not config .feishu :
    logger .error ("Feishu configuration not found!")
    sys .exit (1 )

feishu_client =FeishuClient (config .feishu .app_id ,config .feishu .app_secret )


notification_sender =NotificationSender (feishu_client )


webhook_handler =WebhookHandler (
session_manager ,
notification_sender ,
user_mapping_service 
)


app =FastAPI (
title ="Feishu Bot Webhook Service",
description ="Claude Code 远程控制机器人 Webhook 服务",
version ="1.0.0"
)


@app .get ("/health")
async def health_check ():

    return {
    "status":"healthy",
    "service":"webhook",
    "feishu_app_id":config .feishu .app_id 
    }


@app .post ("/webhook/notification",response_model =WebhookResponse )
async def receive_notification (request :Request ):

    try :

        body =await request .body ()
        body_str =body .decode ('utf-8')


        try :
            json_data =json .loads (body_str )
        except json .JSONDecodeError :

            logger .info ("Attempting to fix malformed JSON")


            if body_str .startswith ("'")and body_str .endswith ("';"):
                body_str =body_str [1 :-2 ]
            elif body_str .startswith ("'")and body_str .endswith ("'"):
                body_str =body_str [1 :-1 ]


            body_str =re .sub (r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:',r'\1"\2":',body_str )


            body_str =re .sub (r':(\{\{[^}]+\}\})',r':"\1"',body_str )

            body_str =re .sub (r':\s*([^,{}"}\[\]"\s][^,{}"}]*?)(?=[,}])',
            lambda m :f': "{m .group (1 ).strip ()}"'if not m .group (1 ).strip ().replace ('.','').replace ('-','').isdigit ()
            and m .group (1 ).strip ()not in ['true','false','null']else f': {m .group (1 ).strip ()}',
            body_str )

            json_data =json .loads (body_str )
            logger .info (f"Successfully parsed fixed JSON: {json_data }")


        req =WebhookRequest (**json_data )
        return webhook_handler .handle_notification (req )
    except Exception as e :
        logger .error (f"Error handling notification: {e }",exc_info =True )
        raise HTTPException (status_code =500 ,detail =str (e ))


@app .get ("/webhook/session/{token}")
async def get_session (token :str ):

    session =webhook_handler .get_session_info (token )
    if not session :
        raise HTTPException (status_code =404 ,detail ="Session not found")

    return {
    "token":session .token ,
    "user_id":session .user_id ,
    "open_id":session .open_id ,
    "tmux_session":session .tmux_session ,
    "status":session .status ,
    "created_at":session .created_at .isoformat (),
    "expires_at":session .expires_at .isoformat ()if session .expires_at else None 
    }


@app .get ("/webhook/stats")
async def get_stats ():

    return webhook_handler .get_stats ()


@app .post ("/webhook/cleanup")
async def cleanup_sessions ():

    cleaned =webhook_handler .cleanup_expired_sessions ()
    return {"cleaned_sessions":cleaned }


if __name__ =="__main__":
    port =config .webhook .port 
    logger .info (f"Starting webhook service on port {port }")
    logger .info (f"API docs: http://localhost:{port }/docs")

    uvicorn .run (
    app ,
    host =config .webhook .host ,
    port =port ,
    log_level ="info"
    )
