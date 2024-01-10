import asyncio
from notion_client import AsyncClient
from notion_client import APIResponseError
from pprint import pprint

import myenv
# myenv.PAGE_ID
# myenv.NOTION_TOKEN

notion = None
page_id = None

def init(auth=None, target_id=None):
    global notion
    global page_id
    page_id = target_id or myenv.PAGE_ID

    print(f"target page id is {page_id}")
    auth = auth or myenv.NOTION_TOKEN

    print(page_id)
    print(auth)
 
    notion = AsyncClient(auth=auth)
    #pprint(await notion.users.list())

async def upload(text):
    #print("uploading....")
    while True:
        try:
            response = await notion.blocks.children.append(
                block_id = page_id,
                children = [{
                    "object": "block",
                    #"type": "bulleted_list_item", "bulleted_list_item":
                    "type": "paragraph", "paragraph":
                    {
                        "rich_text": [{
                            "type": "text",
                            "text": {
                                "content": text
                            }
                        }]
                    }
                }]
            )
            break

        except APIResponseError as error:
            print(error, error.code)
            break
    #print("dene")


async def main():
   await init() 
   await update("hello")


if __name__ == "__main__":
    asyncio.run(main())

    
    
    



