from phi.model.xai import xAI
from phi.agent import Agent
from phi.playground import Playground, serve_playground_app
from phi.storage.agent.sqlite import SqlAgentStorage
import requests
import re
import base64
from os import getenv
import json

from dotenv import load_dotenv
load_dotenv()

GITHUB_PAT = getenv("GITHUB_PAT")


def extract_owner_repo(url):
    pattern = r'github\.com/([^/]+)/([^/]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2)
    else:
        raise ValueError("Invalid GitHub URL")


def fetch_repo_structure(owner, repo, path=''):
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    headers = {'Authorization': f'token {GITHUB_PAT}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        contents = response.json()
        paths = []
        for item in contents:
            if item['type'] == 'dir':
                paths.extend(fetch_repo_structure(owner, repo, item['path']))
            else:
                paths.append(item['path'])
        return paths
    else:
        print(f"Failed to fetch {url}: {response.status_code}")
        return []


def get_github_structure(url):
    """
    Fetches the structure of a GitHub repository.

    Args:
        url (str): The URL of the GitHub repository.

    Returns:
        str: JSON string of the repository structure.
    """
    owner, repo = extract_owner_repo(url)
    return json.dumps(fetch_repo_structure(owner, repo))


def fetch_github_file_content(github_url, file_path):
    """
    Fetches the content of a file in a GitHub repository.

    Args:
        github_url (str): The URL of the GitHub repository.
        file_path (str): The path to the file in the repository.

    Returns:
        str: The content of the file.
    """
    owner, repo = extract_owner_repo(github_url)
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{file_path}'
    headers = {'Authorization': f'token {GITHUB_PAT}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = response.json()
        if content['encoding'] == 'base64':
            decoded_content = base64.b64decode(
                content['content']).decode('utf-8')
            return decoded_content
        else:
            return content['content']
    else:
        print(f"Failed to fetch {url}: {
              response.status_code} - {response.json().get('message')}")
        return ''


analyst_agent = Agent(
    name="Github Analyst",
    model=xAI(id="grok-beta"),
    markdown=True,
    instructions=["""
    You are the best code infrastructure analyst who could spot the issues from a mile away.
    The user provides you with a url to github repo, you would give it a rating based on multiple metrics.
    You do this by:
     1. identifying what the repository is about, and how well the files are organized by getting the structure of the repository.
     2. Identify how many packages are present in the repository.
     3. For every package, Check the dependencies, how good they are. and how well they are managed.Identify the path to relevant file(s) you need to analyze from the structure obtained
     4. The Repositories might contain multiple packages. The user wants analysis on all of them. DO NOT MISS ANY PACKAGE USED IN THE REPOSITORY.
     5. Whether a good package manager is used.

    You respond with a score. Your Analysis is the best, thorough and as air tight as it can get.
    Do not inform user about what you doing in the background for the analysis.
    Give complaints on specific dependeniencies if any.
    Give complaints on the organization of the repository if any.
    Give complaints on package manager if any.
    Be as specific as possible with your analysis. Every Complaint should be backed by a proof.
    No need to give vague suggestions on broader things. Just be specific.
                  
    Response Structure Per Package Found:
    Rating - 1 to 10
    Concerns - List of complaints with proofs for every compliant.
    """],
    tools=[get_github_structure, fetch_github_file_content],
    storage=SqlAgentStorage(table_name="finance_agent", db_file="agents.db"),
    add_history_to_messages=True,
)


# def main(github_url):
#     owner, repo = extract_owner_repo(github_url)
#     data = fetch_repo_structure(owner, repo)
#     print(data)


# # Example usage
# github_url = 'https://github.com/santosh898/profile'
# main(github_url)


app = Playground(agents=[analyst_agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("index:app", reload=True)
