"""
Webhook 服务 - Python 实现
对应 Go 版本: cmd/webhook/main.go
"""

from fastapi import FastAPI ,HTTPException 
from pydantic import BaseModel ,Field 
from typing import Optional 
import logging 
from datetime import datetime 

logger =logging .getLogger (__name__ )




class WebhookRequest (BaseModel ):

    type :str =Field (...,description ="通知类型: completed, waiting, error")
    user_id :str =Field (...,description ="用户ID")
    open_id :str =Field (...,description ="飞书OpenID")
    project_name :str =Field (default ="",description ="项目名称")
    description :str =Field (default ="",description ="描述")
    working_dir :str =Field (default ="",description ="工作目录")
    tmux_session :str =Field (...,description ="Tmux会话名称")


class WebhookResponse (BaseModel ):

    success :bool 
    token :Optional [str ]=None 
    message :str =""
    error :Optional [str ]=None 


class SessionInfo (BaseModel ):

    token :str 
    user_id :str 
    open_id :str 
    tmux_session :str 
    status :str 
    created_at :str 
    expires_at :Optional [str ]




class WebhookHandler :


    def __init__ (self ,session_manager ,notification_sender ,user_mapping_service =None ):
        self .session_manager =session_manager 
        self .notification_sender =notification_sender 
        self .user_mapping_service =user_mapping_service 

    def handle_notification (self ,req :WebhookRequest )->WebhookResponse :

        logger .info (
        f"Received notification: type={req .type }, "
        f"project={req .project_name }, user={req .user_id }"
        )


        if not self ._validate_request (req ):
            return WebhookResponse (
            success =False ,
            error ="Invalid request parameters"
            )


        real_open_id =self ._resolve_open_id (req .user_id ,req .open_id )
        if not real_open_id :
            return WebhookResponse (
            success =False ,
            error ="Failed to resolve user OpenID"
            )


        try :
            session =self .session_manager .create_session (
            user_id =req .user_id ,
            open_id =real_open_id ,
            tmux_session =req .tmux_session ,
            working_dir =req .working_dir ,
            description =req .description ,
            status =self ._map_notification_to_status (req .type )
            )
        except Exception as e :
            logger .error (f"Failed to create session: {e }")
            return WebhookResponse (
            success =False ,
            error =f"Failed to create session: {str (e )}"
            )


        try :
            self ._send_notification (session ,req )
        except Exception as e :
            logger .error (f"Failed to send notification: {e }")

            self .session_manager .delete_session (session .token )
            return WebhookResponse (
            success =False ,
            error =f"Failed to send notification: {str (e )}"
            )

        logger .info (f"Successfully processed notification, token: {session .token }")

        return WebhookResponse (
        success =True ,
        token =session .token ,
        message =f"Notification sent successfully with token {session .token }"
        )

    def _validate_request (self ,req :WebhookRequest )->bool :

        valid_types =["completed","waiting","error"]
        if req .type not in valid_types :
            logger .error (f"Invalid notification type: {req .type }")
            return False 

        if not req .user_id or not req .open_id or not req .tmux_session :
            logger .error ("Missing required fields")
            return False 

        return True 

    def _resolve_open_id (self ,user_id :str ,open_id :str )->Optional [str ]:

        if self .user_mapping_service is None :
            logger .warning ("User mapping service not available, using provided OpenID")
            return open_id 


        if open_id in ["your_open_id","$FEISHU_OPEN_ID"]:

            resolved =self .user_mapping_service .resolve_open_id (user_id ,open_id )
            if resolved :
                logger .info (f"Resolved OpenID: {open_id } -> {resolved } for user {user_id }")
                return resolved 

        return open_id 

    def _map_notification_to_status (self ,notification_type :str )->str :

        mapping ={
        "completed":"completed",
        "waiting":"waiting",
        "error":"active"
        }
        return mapping .get (notification_type ,"active")

    def _send_notification (self ,session ,req :WebhookRequest ):

        notification_data ={
        "type":req .type ,
        "user_id":req .user_id ,
        "open_id":session .open_id ,
        "token":session .token ,
        "project_name":req .project_name ,
        "description":req .description ,
        "working_dir":req .working_dir ,
        "tmux_session":req .tmux_session ,
        "timestamp":datetime .now ()
        }


        if req .type =="completed":
            self .notification_sender .send_task_completed_notification (notification_data )
        elif req .type =="waiting":
            self .notification_sender .send_task_waiting_notification (notification_data )
        elif req .type =="error":
            self .notification_sender .send_error_notification (notification_data )




def create_app (session_manager ,notification_sender ,user_mapping_service =None ):

    app =FastAPI (
    title ="Feishu Bot Webhook Service",
    description ="Claude Code 远程控制机器人 Webhook 服务",
    version ="1.0.0"
    )


    webhook_handler =WebhookHandler (
    session_manager ,
    notification_sender ,
    user_mapping_service 
    )

    @app .get ("/health")
    async def health_check ():

        return {
        "status":"healthy",
        "service":"webhook",
        "timestamp":datetime .now ().isoformat ()
        }

    @app .post ("/webhook/notification",response_model =WebhookResponse )
    async def receive_notification (req :WebhookRequest ):

        try :
            return webhook_handler .handle_notification (req )
        except Exception as e :
            logger .error (f"Error handling notification: {e }")
            raise HTTPException (status_code =500 ,detail ="Internal server error")

    @app .get ("/webhook/session/{token}")
    async def get_session_info (token :str ):

        session =session_manager .get_session (token )
        if session is None :
            raise HTTPException (status_code =404 ,detail ="Session not found")

        return SessionInfo (
        token =session .token ,
        user_id =session .user_id ,
        open_id =session .open_id ,
        tmux_session =session .tmux_session ,
        status =session .status ,
        created_at =session .created_at .isoformat (),
        expires_at =session .expires_at .isoformat ()if session .expires_at else None 
        )

    @app .get ("/webhook/stats")
    async def get_stats ():

        all_sessions =session_manager .list_sessions ()

        status_counts ={}
        for session in all_sessions :
            status_counts [session .status ]=status_counts .get (session .status ,0 )+1 

        return {
        "total_sessions":len (all_sessions ),
        "active_sessions":sum (1 for s in all_sessions if s .status =="active"),
        "status_counts":status_counts ,
        "timestamp":datetime .now ().isoformat ()
        }

    @app .post ("/webhook/cleanup")
    async def cleanup_sessions ():

        cleaned =session_manager .cleanup_expired_sessions ()
        return {
        "cleaned_sessions":cleaned ,
        "message":f"Cleaned {cleaned } expired sessions"
        }

    return app 




if __name__ =='__main__':
    import uvicorn 
    from pathlib import Path 


    logging .basicConfig (
    level =logging .INFO ,
    format ='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


    class MockSessionManager :

        def __init__ (self ):
            self .sessions ={}

        def create_session (self ,**kwargs ):
            from dataclasses import dataclass 
            from datetime import datetime ,timedelta 

            @dataclass 
            class MockSession :
                token :str ="ABC12345"
                user_id :str =kwargs .get ('user_id','')
                open_id :str =kwargs .get ('open_id','')
                tmux_session :str =kwargs .get ('tmux_session','')
                status :str =kwargs .get ('status','active')
                created_at :datetime =datetime .now ()
                expires_at :datetime =datetime .now ()+timedelta (hours =24 )

            return MockSession ()

        def get_session (self ,token ):
            return None 

        def list_sessions (self ,user_id =None ):
            return []

        def cleanup_expired_sessions (self ):
            return 0 

    class MockNotificationSender :

        def send_task_completed_notification (self ,data ):
            logger .info (f"Sending completed notification: {data ['token']}")

        def send_task_waiting_notification (self ,data ):
            logger .info (f"Sending waiting notification: {data ['token']}")

        def send_error_notification (self ,data ):
            logger .info (f"Sending error notification: {data ['token']}")


    session_manager =MockSessionManager ()
    notification_sender =MockNotificationSender ()
    app =create_app (session_manager ,notification_sender )


    logger .info ("Starting webhook service on http://0.0.0.0:8080")
    uvicorn .run (app ,host ="0.0.0.0",port =8080 )
