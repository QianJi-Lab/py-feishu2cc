"""
Bot 服务入口 - 接收飞书消息事件并处理命令
"""

import os 
import sys 
import logging 
import json 
from pathlib import Path 
from typing import Dict ,Any 

sys .path .insert (0 ,str (Path (__file__ ).parent .parent /'src'))

from fastapi import FastAPI ,Request ,HTTPException 
from fastapi .responses import JSONResponse 
import uvicorn 

from feishu_bot .session import SessionManager ,SessionConfig 
from feishu_bot .config import get_config 
from feishu_bot .bot import FeishuClient 
from feishu_bot .command import CommandParser ,ClaudeCliExecutor ,ClaudeCliDirectExecutor 
from feishu_bot .notification import NotificationSender 
import platform 


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

if not config .feishu :
    logger .error ("Feishu configuration not found!")
    sys .exit (1 )

feishu_client =FeishuClient (config .feishu .app_id ,config .feishu .app_secret )
notification_sender =NotificationSender (feishu_client )


logger .info ("Using Claude CLI executor for automated remote control")
command_executor =ClaudeCliExecutor (session_manager )
direct_message_executor =ClaudeCliDirectExecutor (session_manager )

command_parser =CommandParser ()


app =FastAPI (
title ="Feishu Bot Service",
description ="飞书机器人服务 - 接收消息和处理命令",
version ="1.0.0"
)


class MessageHandler :


    def __init__ (self ):
        self .session_manager =session_manager 
        self .command_executor =command_executor 
        self .direct_message_executor =direct_message_executor 
        self .command_parser =command_parser 
        self .notification_sender =notification_sender 
        self .feishu_client =feishu_client 

    async def handle_message (self ,event_data :Dict [str ,Any ])->bool :

        try :

            message =event_data .get ('message',{})
            content_str =message .get ('content','{}')


            try :
                content =json .loads (content_str )
                text =content .get ('text','').strip ()
            except :
                text =content_str .strip ()

            if not text :
                return False 

            logger .info (f"Received message: {text }")


            sender =event_data .get ('sender',{})
            sender_id =sender .get ('sender_id',{})
            open_id =sender_id .get ('open_id','')


            if text .startswith ('/sessions'):
                await self .handle_sessions_command (open_id )
                return True 
            elif text .startswith ('/help'):
                await self .handle_help_command (open_id )
                return True 


            parsed =self .command_parser .parse_remote_command (text )
            if parsed :
                token ,command =parsed 
                await self .handle_remote_command (token ,command ,open_id )
                return True 


            if self .direct_message_executor :
                await self .handle_direct_message (text ,open_id )
                return True 

            return False 

        except Exception as e :
            logger .error (f"Error handling message: {e }",exc_info =True )
            return False 

    async def handle_remote_command (self ,token :str ,command :str ,open_id :str ):

        logger .info (f"Executing remote command: token={token }, command={command }")


        session =self .session_manager .get_session (token )
        if not session :
            self .feishu_client .send_text_message (
            open_id ,
            f"❌ 令牌无效: {token }\n\n请检查令牌是否正确或是否已过期。"
            )
            return 


        result =self .command_executor .execute_command (token ,command ,session .user_id )


        if result .success :
            message =(
            f"✅ 命令执行成功\n"
            f"令牌: {token }\n"
            f"命令: {command }\n"
            f"方法: {result .method }\n"
            f"输出: {result .output }\n"
            f"耗时: {result .exec_time_ms }ms"
            )
        else :
            message =(
            f"❌ 命令执行失败\n"
            f"令牌: {token }\n"
            f"命令: {command }\n"
            f"错误: {result .error }\n"
            f"耗时: {result .exec_time_ms }ms"
            )

        self .feishu_client .send_text_message (open_id ,message )

    async def handle_direct_message (self ,message :str ,open_id :str ):

        logger .info (f"Handling direct message: {message [:50 ]}...")


        result =self .direct_message_executor .send_message (open_id ,message )


        if result .success :
            self .feishu_client .send_text_message (open_id ,result .output )
        else :
            self .feishu_client .send_text_message (
            open_id ,
            f"❌ 发送失败\n\n{result .error }"
            )

    async def handle_sessions_command (self ,open_id :str ):

        sessions =self .session_manager .list_sessions ()

        if not sessions :
            self .feishu_client .send_text_message (
            open_id ,
            "📋 当前没有活跃的会话"
            )
            return 

        message_lines =["📋 活跃会话列表:\n"]
        for session in sessions :
            message_lines .append (
            f"令牌: {session .token }\n"
            f"  Tmux: {session .tmux_session }\n"
            f"  状态: {session .status }\n"
            f"  创建时间: {session .created_at .strftime ('%Y-%m-%d %H:%M:%S')}\n"
            )

        self .feishu_client .send_text_message (open_id ,'\n'.join (message_lines ))

    async def handle_help_command (self ,open_id :str ):

        help_text =(
        "📖 飞书 Claude Code 远程控制机器人\n\n"
        "🔹 命令格式:\n"
        "  <令牌>: <命令>\n"
        "  例: ABC12345: ls -la\n\n"
        "🔹 特殊命令:\n"
        "  /sessions - 查看活跃会话\n"
        "  /help - 显示此帮助\n\n"
        "🔹 使用流程:\n"
        "  1. Claude Code 任务完成后会发送通知\n"
        "  2. 通知中包含8位令牌(如: ABC12345)\n"
        "  3. 使用格式 '<令牌>: <命令>' 发送命令\n"
        "  4. 机器人会在对应的 tmux 会话中执行\n"
        "  5. 执行结果会实时反馈给你\n"
        )

        self .feishu_client .send_text_message (open_id ,help_text )


message_handler =MessageHandler ()


@app .get ("/health")
async def health_check ():

    return {
    "status":"healthy",
    "service":"bot",
    "sessions":len (session_manager .list_sessions ())
    }


@app .post ("/webhook/event")
async def handle_event (request :Request ):

    try :

        raw_body =await request .body ()
        logger .info (f"=== Raw request body ===")
        logger .info (raw_body .decode ('utf-8')[:500 ])


        import json 
        body =json .loads (raw_body .decode ('utf-8'))
        logger .info (f"=== Parsed JSON ===")
        logger .info (f"Body keys: {list (body .keys ())}")


        if body .get ('type')=='url_verification':
            challenge =body .get ('challenge','')
            logger .info (f"URL verification: {challenge }")
            return JSONResponse ({"challenge":challenge })


        event_type =body .get ('type')or body .get ('header',{}).get ('event_type','')
        event =body .get ('event',{})

        logger .info (f"=== Event info ===")
        logger .info (f"Event type: {event_type }")
        logger .info (f"Event keys: {list (event .keys ())if event else 'None'}")


        if event_type =='im.message.receive_v1':

            message =event .get ('message',{})

            msg_type =message .get ('message_type')or message .get ('msg_type','')

            logger .info (f"Message type: {msg_type }")
            logger .info (f"Message content: {message .get ('content','')}")


            if msg_type =='text':
                logger .info ("Processing text message...")
                await message_handler .handle_message (event )
            else :
                logger .info (f"Ignored message type: {msg_type }")
        else :
            logger .warning (f"Unknown event type: {event_type }")

        return JSONResponse ({"code":0 ,"msg":"success"})

    except Exception as e :
        logger .error (f"Error handling event: {e }",exc_info =True )
        return JSONResponse (
        {"code":-1 ,"msg":str (e )},
        status_code =500 
        )


@app .get ("/stats")
async def get_stats ():

    sessions =session_manager .list_sessions ()
    return {
    "total_sessions":len (sessions ),
    "active_sessions":sum (1 for s in sessions if s .status =='active'),
    "feishu_app_id":config .feishu .app_id 
    }


if __name__ =="__main__":
    port =8081 
    logger .info (f"Starting bot service on port {port }")
    logger .info (f"Event webhook URL: http://localhost:{port }/webhook/event")
    logger .info ("Please configure this URL in Feishu Open Platform")

    uvicorn .run (
    app ,
    host ="0.0.0.0",
    port =port ,
    log_level ="info"
    )


import os 
import sys 
import logging 
from pathlib import Path 
from dotenv import load_dotenv 


project_root =Path (__file__ ).parent .parent 


load_dotenv (project_root /'.env')


sys .path .insert (0 ,str (project_root /'src'))
from feishu_bot .session import SessionManager ,SessionConfig 
from feishu_bot .config import get_config 
from feishu_bot .bot import FeishuClient 
from feishu_bot .command import CommandParser ,TmuxCommandExecutor 
from feishu_bot .notification import NotificationSender 


logging .basicConfig (
level =logging .INFO ,
format ='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger =logging .getLogger (__name__ )


def main ():

    config =get_config ()


    session_manager =SessionManager (
    config .session .storage_file ,
    SessionConfig (
    token_length =config .session .token_length ,
    expiration_hours =config .session .expiration_hours ,
    cleanup_interval_minutes =config .session .cleanup_interval_minutes 
    )
    )

    if not config .feishu :
        logger .error ("Feishu configuration not found!")
        sys .exit (1 )

    feishu_client =FeishuClient (config .feishu .app_id ,config .feishu .app_secret )
    notification_sender =NotificationSender (feishu_client )
    command_executor =TmuxCommandExecutor (session_manager )
    parser =CommandParser ()

    logger .info ("Bot service initialized")
    logger .info ("Note: WebSocket integration requires additional implementation")
    logger .info ("For now, use Webhook service to receive notifications")







if __name__ =="__main__":
    main ()
