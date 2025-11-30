"""
Webhook 处理器
"""

import logging 
from datetime import datetime 
from typing import Optional 

from ..session import SessionManager ,STATUS_ACTIVE ,STATUS_COMPLETED ,STATUS_WAITING 
from .types import WebhookRequest ,WebhookResponse ,TYPE_COMPLETED ,TYPE_WAITING ,TYPE_ERROR 

logger =logging .getLogger (__name__ )


class WebhookHandler :


    def __init__ (self ,session_manager :SessionManager ,notification_sender ,user_mapping_service =None ):
        self .session_manager =session_manager 
        self .notification_sender =notification_sender 
        self .user_mapping_service =user_mapping_service 

    def handle_notification (self ,req :WebhookRequest )->WebhookResponse :

        logger .info (f"Received notification: type={req .type }, project={req .project_name }, user={req .user_id }")


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

        valid_types =[TYPE_COMPLETED ,TYPE_WAITING ,TYPE_ERROR ]
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

        resolved =self .user_mapping_service .resolve_open_id (user_id ,open_id )
        if resolved and resolved !=open_id :
            logger .info (f"Resolved OpenID: {open_id } -> {resolved } for user {user_id }")

        return resolved 

    def _map_notification_to_status (self ,notification_type :str )->str :

        mapping ={
        TYPE_COMPLETED :STATUS_COMPLETED ,
        TYPE_WAITING :STATUS_WAITING ,
        TYPE_ERROR :STATUS_ACTIVE 
        }
        return mapping .get (notification_type ,STATUS_ACTIVE )

    def _send_notification (self ,session ,req :WebhookRequest ):

        notification_data ={
        'type':req .type ,
        'user_id':req .user_id ,
        'open_id':session .open_id ,
        'token':session .token ,
        'project_name':req .project_name ,
        'description':req .description ,
        'working_dir':req .working_dir ,
        'tmux_session':req .tmux_session ,
        'task_output':req .task_output ,
        'timestamp':datetime .now ()
        }


        if req .type ==TYPE_COMPLETED :
            self .notification_sender .send_task_completed_notification (notification_data )
        elif req .type ==TYPE_WAITING :
            self .notification_sender .send_task_waiting_notification (notification_data )
        elif req .type ==TYPE_ERROR :
            self .notification_sender .send_task_completed_notification (notification_data )

    def get_session_info (self ,token :str ):

        return self .session_manager .get_session (token )

    def cleanup_expired_sessions (self )->int :

        return self .session_manager .cleanup_expired_sessions ()

    def get_stats (self )->dict :

        all_sessions =self .session_manager .list_sessions ()

        status_counts ={}
        for session in all_sessions :
            status_counts [session .status ]=status_counts .get (session .status ,0 )+1 

        return {
        'total_sessions':len (all_sessions ),
        'active_sessions':sum (1 for s in all_sessions if s .status ==STATUS_ACTIVE ),
        'status_counts':status_counts ,
        'timestamp':datetime .now ().isoformat ()
        }
