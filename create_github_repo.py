import os
import requests

def create_github_repo(repo_name, description):
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GitHub token not found in environment variables")

    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    data = {
        'name': repo_name,
        'description': description,
        'private': False
    }

    response = requests.post('https://api.github.com/user/repos', headers=headers, json=data)

    if response.status_code == 201:
        print(f"Repository '{repo_name}' created successfully!")
        return response.json()['html_url']
    else:
        print(f"Failed to create repository. Status code: {response.status_code}")
        print(f"Error message: {response.json().get('message', 'Unknown error')}")
        return None

if __name__ == '__main__':
    repo_name = 'AI-Manifestation-Script-Generator'
    description = 'An AI-powered manifestation script generator app with user profiles and a community board using Flask and Vanilla JS'
    repo_url = create_github_repo(repo_name, description)
    
    if repo_url:
        print(f"Repository URL: {repo_url}")
        print("Now, you can add the remote origin to your local repository using:")
        print(f"git remote add origin {repo_url}")
        print("Then push your code to GitHub with:")
        print("git push -u origin main")
