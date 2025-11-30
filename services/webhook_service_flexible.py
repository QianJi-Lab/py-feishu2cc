"""
Webhook 服务入口 (宽松版 - 接受任意 JSON)
"""

import os 
import sys 
import logging 
from pathlib import Path 


sys .path .insert (0 ,str (Path (__file__ ).parent .parent /'src'))

from fastapi import FastAPI ,Request 
from fastapi .responses import JSONResponse 
import uvicorn 

from feishu_bot .session import SessionManager ,SessionConfig 
from feishu_bot .config import get_config 
from feishu_bot .security import UserMappingService 
from feishu_bot .bot import FeishuClient 
from feishu_bot .notification import NotificationSender 


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


app =FastAPI (
title ="Feishu Bot Webhook Service (Flexible)",
description ="Claude Code 远程控制机器人 Webhook 服务 (宽松版)",
version ="1.0.0"
)


@app .get ("/health")
async def health_check ():

    return {
    "status":"healthy",
    "service":"webhook",
    "feishu_app_id":config .feishu .app_id 
    }


@app .post ("/webhook/notification")
async def receive_notification (request :Request ):

    try :

        body =await request .body ()
        import json 
        data =json .loads (body )


        logger .info ("="*60 )
        logger .info ("📥 Received webhook notification:")
        logger .info (json .dumps (data ,indent =2 ,ensure_ascii =False ))
        logger .info ("="*60 )


        event =data .get ('event','unknown')
        task_id =data .get ('task_id','unknown')
        user_id =data .get ('user_id')or config .feishu .user_id 
        tmux_session =data .get ('tmux_session','main')


        notification_data =data .get ('notification',{})
        message =notification_data .get ('message',data .get ('message','未知通知'))
        details =notification_data .get ('details',data .get ('details',''))

        logger .info (f"Event: {event }, Task: {task_id }, User: {user_id }")


        session =session_manager .create_session (
        user_id =user_id ,
        tmux_session =tmux_session 
        )

        logger .info (f"✅ Created session: {session .token }")


        open_id =None 
        if user_mapping_service :
            open_id =user_mapping_service .get_open_id (user_id )

        if not open_id :
            open_id =config .feishu .open_id 
            logger .warning (f"User {user_id } not in whitelist, using default open_id")


        notification_text =f"""【Claude Code 任务通知】
事件: {event }
任务ID: {task_id }
会话: {tmux_session }

{message }

{details }

Token: {session .token }
24小时内有效,回复 "{session .token }: 命令" 来执行命令
"""

        success =notification_sender .send_notification (open_id ,notification_text )

        if success :
            logger .info (f"✅ Notification sent to {open_id }")
        else :
            logger .error (f"❌ Failed to send notification to {open_id }")

        return {
        "status":"success",
        "token":session .token ,
        "message":"Notification received and session created"
        }

    except Exception as e :
        logger .error (f"Error handling notification: {e }",exc_info =True )
        return JSONResponse (
        status_code =500 ,
        content ={"status":"error","message":str (e )}
        )


@app .get ("/webhook/session/{token}")
async def get_session (token :str ):

    session =session_manager .get_session (token )
    if not session :
        return JSONResponse (
        status_code =404 ,
        content ={"error":"Session not found"}
        )

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

    sessions =session_manager .list_sessions ()
    return {
    "total_sessions":len (sessions ),
    "active_sessions":len ([s for s in sessions if s .status =="active"]),
    "sessions":[
    {
    "token":s .token ,
    "user_id":s .user_id ,
    "tmux_session":s .tmux_session ,
    "status":s .status ,
    "created_at":s .created_at .isoformat ()
    }
    for s in sessions 
    ]
    }


@app .post ("/webhook/cleanup")
async def cleanup_sessions ():

    cleaned =session_manager .cleanup_expired_sessions ()
    return {"cleaned_sessions":cleaned }


if __name__ =="__main__":
    port =config .webhook .port 
    logger .info (f"Starting webhook service (flexible) on port {port }")
    logger .info (f"API docs: http://localhost:{port }/docs")

    uvicorn .run (
    app ,
    host =config .webhook .host ,
    port =port ,
    log_level ="info"
    )
