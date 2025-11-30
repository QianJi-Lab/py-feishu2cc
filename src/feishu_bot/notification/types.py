"""
Notification 数据模型
"""

from pydantic import BaseModel ,Field 
from typing import Optional 
from datetime import datetime 


class WebhookRequest (BaseModel ):

    type :str =Field (...,description ="通知类型: completed, waiting, error")
    user_id :str =Field (...,description ="用户ID")
    open_id :str =Field (...,description ="飞书OpenID")
    project_name :str =Field (default ="",description ="项目名称")
    description :str =Field (default ="",description ="描述")
    working_dir :str =Field (default ="",description ="工作目录")
    tmux_session :str =Field (...,description ="Tmux会话名称")
    task_output :Optional [str ]=Field (default ="",description ="任务执行输出结果")


class WebhookResponse (BaseModel ):

    success :bool 
    token :Optional [str ]=None 
    message :str =""
    error :Optional [str ]=None 


class TaskNotification (BaseModel ):

    type :str 
    user_id :str 
    open_id :str 
    token :str 
    project_name :str =""
    description :str =""
    working_dir :str =""
    tmux_session :str =""
    task_output :str =""
    timestamp :datetime =Field (default_factory =datetime .now )



TYPE_COMPLETED ="completed"
TYPE_WAITING ="waiting"
TYPE_ERROR ="error"
