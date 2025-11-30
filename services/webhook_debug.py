"""
Webhook 调试服务 - 打印所有请求数据
"""

import sys 
from pathlib import Path 
sys .path .insert (0 ,str (Path (__file__ ).parent .parent /'src'))

from fastapi import FastAPI ,Request 
import uvicorn 
import json 

app =FastAPI (title ="Webhook Debug Service")


@app .post ("/webhook/notification")
async def debug_notification (request :Request ):



    body =await request .body ()

    print ("="*80 )
    print ("📥 Received Webhook Request")
    print ("="*80 )


    print ("\n📋 Headers:")
    for key ,value in request .headers .items ():
        print (f"  {key }: {value }")


    print ("\n📦 Raw Body:")
    print (body .decode ('utf-8'))


    try :
        body_str =body .decode ('utf-8')


        try :
            json_data =json .loads (body_str )
        except json .JSONDecodeError :


            if body_str .startswith ("'")and body_str .endswith ("';"):
                body_str =body_str [1 :-2 ]
            elif body_str .startswith ("'")and body_str .endswith ("'"):
                body_str =body_str [1 :-1 ]


            import re 
            body_str =re .sub (r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:',r'\1"\2":',body_str )



            body_str =re .sub (r':(\{\{[^}]+\}\})',r':"\1"',body_str )

            body_str =re .sub (r':\s*([^,{}"}\[\]"\s][^,{}"}]*?)(?=[,}])',
            lambda m :f': "{m .group (1 ).strip ()}"'if not m .group (1 ).strip ().replace ('.','').replace ('-','').isdigit ()
            and m .group (1 ).strip ()not in ['true','false','null']else f': {m .group (1 ).strip ()}',
            body_str )

            json_data =json .loads (body_str )

        print ("\n📊 Parsed JSON:")
        print (json .dumps (json_data ,indent =2 ,ensure_ascii =False ))
    except Exception as e :
        print (f"\n❌ Failed to parse JSON: {e }")
        print (f"\n🔧 Attempted to parse: {body_str if 'body_str'in locals ()else 'N/A'}")

    print ("\n"+"="*80 )

    return {"status":"received","message":"Check console for details"}


@app .get ("/health")
async def health ():
    return {"status":"ok"}


if __name__ =="__main__":
    print ("🔍 Starting webhook debug service on http://localhost:8080")
    print ("📝 This will print all incoming webhook requests")
    print ()

    uvicorn .run (
    app ,
    host ="0.0.0.0",
    port =8080 ,
    log_level ="info"
    )
