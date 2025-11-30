"""
通知发送器
"""

import logging 
from typing import Optional 

logger =logging .getLogger (__name__ )


class NotificationSender :


    def __init__ (self ,feishu_client ):

        self .feishu_client =feishu_client 

    def send_task_completed_notification (self ,notification :dict )->bool :

        try :
            message =self ._format_completed_message (notification )
            return self .feishu_client .send_text_message (
            notification ['open_id'],
            message 
            )
        except Exception as e :
            logger .error (f"Failed to send completed notification: {e }")
            return False 

    def send_task_waiting_notification (self ,notification :dict )->bool :

        try :
            message =self ._format_waiting_message (notification )
            return self .feishu_client .send_text_message (
            notification ['open_id'],
            message 
            )
        except Exception as e :
            logger .error (f"Failed to send waiting notification: {e }")
            return False 

    def send_command_result_notification (self ,open_id :str ,result :dict )->bool :

        try :
            message =self ._format_result_message (result )
            return self .feishu_client .send_text_message (open_id ,message )
        except Exception as e :
            logger .error (f"Failed to send result notification: {e }")
            return False 

    def send_text_notification (self ,open_id :str ,text :str )->bool :

        try :
            return self .feishu_client .send_text_message (open_id ,text )
        except Exception as e :
            logger .error (f"Failed to send text notification: {e }")
            return False 

    def _format_completed_message (self ,notification :dict )->str :


        message =f"""🎉 任务执行完成

项目: {notification .get ('project_name','Unknown')}
描述: {notification .get ('description','Task completed')}
工作目录: {notification .get ('working_dir','N/A')}"""


        task_output =notification .get ('task_output','').strip ()
        if task_output :

            max_output_length =1000 
            if len (task_output )>max_output_length :
                task_output =task_output [:max_output_length ]+"\n\n... (输出过长，已截断)"
            message +=f"\n\n📝 任务输出:\n{task_output }"


        message +=f"""

🔑 远程控制令牌: {notification ['token']}

使用方法:
发送消息 "{notification ['token']}: <你的命令>" 来远程控制

示例:
{notification ['token']}: git status
{notification ['token']}: npm test
{notification ['token']}: ls -la

令牌有效期: 24小时"""

        return message 

    def _format_waiting_message (self ,notification :dict )->str :

        return f"""⏳ 等待用户输入

项目: {notification .get ('project_name','Unknown')}
描述: {notification .get ('description','Waiting for input')}
工作目录: {notification .get ('working_dir','N/A')}

🔑 远程控制令牌: {notification ['token']}

请发送下一步指令:
格式: {notification ['token']}: <你的命令>

令牌有效期: 24小时"""

    def _format_result_message (self ,result :dict )->str :

        if result .get ('success'):
            return f"""✅ 命令执行成功

令牌: {result .get ('token','N/A')}
命令: {result .get ('command','N/A')}
方法: {result .get ('method','N/A')}
耗时: {result .get ('exec_time_ms',0 )}ms

输出: {result .get ('output','No output')}"""
        else :
            return f"""❌ 命令执行失败

令牌: {result .get ('token','N/A')}
命令: {result .get ('command','N/A')}
错误: {result .get ('error','Unknown error')}"""
