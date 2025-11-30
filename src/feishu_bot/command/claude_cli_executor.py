"""
Claude CLI 执行器 - 真正的远程自动化执行

使用 Claude CLI 实现完全自动化的远程控制:
- 无需人工干预
- 直接通过 CLI 与 Claude 交互
- 支持继续对话
"""

import subprocess 
import logging 
import json 
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


class ClaudeCliExecutor :


    def __init__ (self ,session_manager ):
        self .session_manager =session_manager 
        from .parser import CommandParser 
        from .validator import CommandValidator 
        self .parser =CommandParser ()
        self .validator =CommandValidator ()
        self ._check_claude_cli ()

    def _check_claude_cli (self ):

        try :
            result =subprocess .run (
            'claude --version',
            capture_output =True ,
            text =True ,
            encoding ='utf-8',
            errors ='ignore',
            timeout =5 ,
            shell =True 
            )
            if result .returncode ==0 :
                logger .info (f"Claude CLI found: {result .stdout .strip ()}")
            else :
                logger .warning ("Claude CLI not found or not working")
        except Exception as e :
            logger .error (f"Failed to check Claude CLI: {e }")

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


        working_dir =session .working_dir 
        if working_dir =="{{cwd}}"or not working_dir :
            working_dir =str (Path .cwd ())


        result =self ._execute_with_claude_cli (command ,working_dir )
        result .token =token 
        result .command =command 
        result .exec_time_ms =self ._calc_exec_time (start_time )


        self .session_manager .update_session (token )

        logger .info (f"Command executed via Claude CLI: token={token }, success={result .success }")
        return result 

    def _execute_with_claude_cli (self ,command :str ,working_dir :str )->CommandResult :

        try :

            escaped_command =command .replace ('"','\\"')


            result =subprocess .run (
            f'claude -p "{escaped_command }"',
            capture_output =True ,
            text =True ,
            encoding ='utf-8',
            errors ='ignore',
            timeout =120 ,
            cwd =working_dir ,
            shell =True 
            )

            if result .returncode ==0 :
                output =result .stdout .strip ()
                return CommandResult (
                token ="",
                command =command ,
                success =True ,
                method ="claude_cli",
                output =output if output else "Command executed successfully"
                )
            else :
                error =result .stderr .strip ()
                return CommandResult (
                token ="",
                command =command ,
                success =False ,
                method ="failed",
                error =f"Claude CLI error: {error }"
                )

        except subprocess .TimeoutExpired :
            return CommandResult (
            token ="",
            command =command ,
            success =False ,
            method ="failed",
            error ="Command execution timed out (120s limit)"
            )
        except Exception as e :
            logger .error (f"Failed to execute with Claude CLI: {e }")
            return CommandResult (
            token ="",
            command =command ,
            success =False ,
            method ="failed",
            error =f"Execution failed: {str (e )}"
            )

    def _calc_exec_time (self ,start_time :datetime )->int :

        delta =datetime .now ()-start_time 
        return int (delta .total_seconds ()*1000 )


class ClaudeCliDirectExecutor :


    def __init__ (self ,session_manager ):
        self .session_manager =session_manager 

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


        working_dir =session .working_dir 
        if working_dir =="{{cwd}}"or not working_dir :
            working_dir =str (Path .cwd ())


        try :

            escaped_message =message .replace ('"','\\"')

            result =subprocess .run (
            f'claude -p "{escaped_message }"',
            capture_output =True ,
            text =True ,
            encoding ='utf-8',
            errors ='ignore',
            timeout =120 ,
            cwd =working_dir ,
            shell =True 
            )


            self .session_manager .update_session (session .token )

            if result .returncode ==0 :
                output =result .stdout .strip ()

                return CommandResult (
                token =session .token ,
                command =message ,
                success =True ,
                method ="claude_cli_auto",
                output =(
                f"🤖 Claude 回复:\n\n{output }\n\n"
                f"───────────────────\n"
                f"🔑 会话令牌: {session .token }\n"
                f"📂 工作目录: {session .working_dir }"
                ),
                exec_time_ms =self ._calc_exec_time (start_time )
                )
            else :
                error =result .stderr .strip ()
                return CommandResult (
                token =session .token ,
                command =message ,
                success =False ,
                method ="failed",
                error =f"Claude 执行失败:\n{error }",
                exec_time_ms =self ._calc_exec_time (start_time )
                )

        except subprocess .TimeoutExpired :
            return CommandResult (
            token =session .token ,
            command =message ,
            success =False ,
            method ="failed",
            error ="⏱️ 执行超时(120秒)\n\n任务可能太复杂,请简化后重试",
            exec_time_ms =self ._calc_exec_time (start_time )
            )
        except Exception as e :
            logger .error (f"Failed to send message via Claude CLI: {e }")
            return CommandResult (
            token =session .token ,
            command =message ,
            success =False ,
            method ="failed",
            error =f"发送消息失败: {str (e )}",
            exec_time_ms =self ._calc_exec_time (start_time )
            )

    def _calc_exec_time (self ,start_time :datetime )->int :

        delta =datetime .now ()-start_time 
        return int (delta .total_seconds ()*1000 )
