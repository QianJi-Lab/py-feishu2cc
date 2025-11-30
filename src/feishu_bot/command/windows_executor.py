"""
Windows Claude Code 命令执行器

又因为在 Windows 上,Claude Code 没有 tmux,所以通过文件系统与 Claude Code 通信:
1. 将用户消息写入临时文件
2. 使用 Claude Code 的 transcript 文件追加用户输入
3. Claude Code 会读取并响应
"""

import os 
import json 
import logging 
import subprocess 
from typing import Optional 
from dataclasses import dataclass 
from datetime import datetime 
from pathlib import Path 

logger =logging .getLogger (__name__ )


@dataclass 
class CommandResult :

    token :str 
    command :str 
    success :bool 
    method :str 
    output :str =""
    error :str =""
    exec_time_ms :int =0 
    timestamp :datetime =None 

    def __post_init__ (self ):
        if self .timestamp is None :
            self .timestamp =datetime .now ()


class WindowsClaudeCodeExecutor :


    def __init__ (self ,session_manager ):
        self .session_manager =session_manager 
        from .parser import CommandParser 
        from .validator import CommandValidator 
        self .parser =CommandParser ()
        self .validator =CommandValidator ()

    def execute_command (self ,token :str ,command :str ,user_id :str )->CommandResult :

        start_time =datetime .now ()


        session =self .session_manager .validate_session (token )
        if session is None :
            return CommandResult (
            token =token ,
            command =command ,
            success =False ,
            method ="failed",
            error ="Session validation failed",
            exec_time_ms =self ._calc_exec_time (start_time )
            )


        if not self .validator .validate_command (command ):
            return CommandResult (
            token =token ,
            command =command ,
            success =False ,
            method ="failed",
            error ="Command validation failed (dangerous command blocked)",
            exec_time_ms =self ._calc_exec_time (start_time )
            )


        try :
            self ._copy_to_clipboard (command )


            self .session_manager .update_session (token )

            return CommandResult (
            token =token ,
            command =command ,
            success =True ,
            method ="windows_clipboard",
            output =f"✅ 命令已复制到剪贴板\n\n请在 Claude Code 窗口中粘贴(Ctrl+V)并发送\n\n命令内容: {command }",
            exec_time_ms =self ._calc_exec_time (start_time )
            )
        except Exception as e :
            logger .error (f"Failed to copy to clipboard: {e }")
            return CommandResult (
            token =token ,
            command =command ,
            success =False ,
            method ="failed",
            error =f"Failed to prepare command: {str (e )}",
            exec_time_ms =self ._calc_exec_time (start_time )
            )

    def _copy_to_clipboard (self ,text :str ):


        try :
            process =subprocess .Popen (
            ['powershell','-command',f'Set-Clipboard -Value "{text }"'],
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE 
            )
            stdout ,stderr =process .communicate (timeout =5 )

            if process .returncode !=0 :
                raise Exception (f"PowerShell error: {stderr .decode ()}")

            logger .info (f"Copied to clipboard: {text [:50 ]}...")
        except Exception as e :
            logger .error (f"Clipboard operation failed: {e }")
            raise 

    def _calc_exec_time (self ,start_time :datetime )->int :

        delta =datetime .now ()-start_time 
        return int (delta .total_seconds ()*1000 )


class WindowsDirectMessageExecutor :


    def __init__ (self ,session_manager ):
        self .session_manager =session_manager 
        self .message_dir =Path ("data/messages")
        self .message_dir .mkdir (parents =True ,exist_ok =True )

    def send_message (self ,open_id :str ,message :str )->CommandResult :

        start_time =datetime .now ()


        session =self .session_manager .get_user_active_session (open_id )

        if not session :
            return CommandResult (
            token ="",
            command =message ,
            success =False ,
            method ="failed",
            error ="没有找到活跃的 Claude Code 会话\n\n请先通过 Claude Code 完成一个任务,获取会话令牌后再试",
            exec_time_ms =self ._calc_exec_time (start_time )
            )


        try :
            self ._copy_to_clipboard (message )


            self .session_manager .update_session (session .token )

            return CommandResult (
            token =session .token ,
            command =message ,
            success =True ,
            method ="windows_direct_message",
            output =(
            f"💬 消息已准备好发送给 Claude Code\n\n"
            f"📋 消息已复制到剪贴板\n"
            f"🔑 会话令牌: {session .token }\n"
            f"📂 工作目录: {session .working_dir }\n\n"
            f"请在 Claude Code 窗口中粘贴(Ctrl+V)并发送\n\n"
            f"💡 提示: 您也可以直接在飞书使用格式 '{session .token }: <命令>' 来执行特定命令"
            ),
            exec_time_ms =self ._calc_exec_time (start_time )
            )

        except Exception as e :
            logger .error (f"Failed to send message: {e }")
            return CommandResult (
            token =session .token ,
            command =message ,
            success =False ,
            method ="failed",
            error =f"发送消息失败: {str (e )}",
            exec_time_ms =self ._calc_exec_time (start_time )
            )

    def _copy_to_clipboard (self ,text :str ):

        try :

            escaped_text =text .replace ('"','`"').replace ('$','`$')

            process =subprocess .Popen (
            ['powershell','-command',f'Set-Clipboard -Value "{escaped_text }"'],
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE 
            )
            stdout ,stderr =process .communicate (timeout =5 )

            if process .returncode !=0 :
                raise Exception (f"PowerShell error: {stderr .decode ()}")

            logger .info (f"Copied to clipboard: {text [:50 ]}...")
        except Exception as e :
            logger .error (f"Clipboard operation failed: {e }")
            raise 

    def _calc_exec_time (self ,start_time :datetime )->int :

        delta =datetime .now ()-start_time 
        return int (delta .total_seconds ()*1000 )
