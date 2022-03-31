from typing import Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel

import requests
import json
import jinja2
import uvicorn

from fastapi.templating import Jinja2Templates

import re
CLEANR = re.compile('<.*?>') 

def cleanhtml(raw_html):
  cleantext = re.sub(CLEANR, '', raw_html)
  return cleantext

func_dict = {
    "cleanhtml": cleanhtml
}

class QueryInputs(BaseModel):
    template: str
    endpoint: str
    content_type: str
    
app = FastAPI()

@app.post("/")
async def root(request: Request, input: QueryInputs):
    
    res = requests.get(input.endpoint)
    
    if res.status_code == 200:
        data = json.loads(res.content)
        
        templates = Jinja2Templates(directory="../templates")
        
        response = templates.TemplateResponse(input.template, {"request" : request, "data": data})
        response.headers['content-type'] = f"{input.content_type}; charset=utf-8"
        
        return response
    else:
        return {"error": "Error in the endpoint request"}
