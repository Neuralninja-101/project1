import requests
from bs4 import BeautifulSoup

def scrape_tds_course():
    url = "https://tds.s-anand.net/2025-01/content.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()  # contains structured TDS content
    else:
        return {}

def scrape_discourse_posts():
    base_url = "https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34.json"
    posts = []
    response = requests.get(base_url)
    if response.status_code != 200:
        return posts

    topic_list = response.json().get("topic_list", {}).get("topics", [])
    for topic in topic_list:
        topic_id = topic.get("id")
        topic_url = f"https://discourse.onlinedegree.iitm.ac.in/t/{topic_id}.json"
        topic_data = requests.get(topic_url).json()
        for post in topic_data.get("post_stream", {}).get("posts", []):
            posts.append({
                "url": f"https://discourse.onlinedegree.iitm.ac.in/t/{topic_id}/{post.get('post_number')}",
                "text": post.get("cooked")
            })
    return posts
