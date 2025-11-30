"""
飞书客户端封装
"""

import logging 
import json 
from lark_oapi import Client 
from lark_oapi .api .im .v1 import (
CreateMessageRequest ,
CreateMessageRequestBody ,
CreateMessageResponse 
)

logger =logging .getLogger (__name__ )


class FeishuClient :


    def __init__ (self ,app_id :str ,app_secret :str ):
        self .app_id =app_id 
        self .app_secret =app_secret 
        self .client =Client .builder ().app_id (app_id ).app_secret (app_secret ).build ()
        logger .info (f"Feishu client initialized: app_id={app_id }")

    def send_text_message (self ,open_id :str ,text :str )->bool :

        try :

            content =json .dumps ({"text":text })

            request =CreateMessageRequest .builder ().receive_id_type ("open_id").request_body (
            CreateMessageRequestBody .builder ()
            .receive_id (open_id )
            .msg_type ("text")
            .content (content )
            .build ()
            ).build ()

            response :CreateMessageResponse =self .client .im .v1 .message .create (request )

            if not response .success ():
                logger .error (f"Failed to send message: {response .code } - {response .msg }")
                return False 

            logger .info (f"Message sent successfully to {open_id }")
            return True 

        except Exception as e :
            logger .error (f"Error sending message: {e }")
            return False 

    def send_card (self ,open_id :str ,card_content :str )->bool :

        try :
            request =CreateMessageRequest .builder ().receive_id_type ("open_id").request_body (
            CreateMessageRequestBody .builder ()
            .receive_id (open_id )
            .msg_type ("interactive")
            .content (card_content )
            .build ()
            ).build ()

            response =self .client .im .v1 .message .create (request )

            if not response .success ():
                logger .error (f"Failed to send card: {response .code } - {response .msg }")
                return False 

            logger .info (f"Card sent successfully to {open_id }")
            return True 

        except Exception as e :
            logger .error (f"Error sending card: {e }")
            return False 
