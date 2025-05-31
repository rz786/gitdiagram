import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()


class AzureDevOpsService:
    def __init__(self, pat: str | None = None):
        self.azure_pat = pat or os.getenv("AZURE_PAT")

    def _get_headers(self):
        if not self.azure_pat:
            return {"Accept": "application/json"}
        token = base64.b64encode(f":{self.azure_pat}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }

    def get_default_branch(self, organization: str, repo: str, project: str | None = None):
        project = project or repo
        api_url = (
            f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo}?api-version=7.0"
        )
        response = requests.get(api_url, headers=self._get_headers())
        if response.status_code == 200:
            data = response.json()
            default_branch = data.get("defaultBranch")
            if default_branch:
                return default_branch.replace("refs/heads/", "")
        return None

    def get_repo_file_paths_as_list(self, organization: str, repo: str, project: str | None = None):
        project = project or repo
        branch = self.get_default_branch(organization, repo, project) or "main"
        api_url = (
            "https://dev.azure.com/"
            f"{organization}/{project}/_apis/git/repositories/{repo}/items"
            f"?recursionLevel=full&versionDescriptor.version={branch}&api-version=7.0"
        )
        response = requests.get(api_url, headers=self._get_headers())
        if response.status_code != 200:
            raise ValueError("Could not fetch repository file tree.")
        data = response.json()

        def should_include_file(path: str) -> bool:
            excluded_patterns = [
                "node_modules/",
                "vendor/",
                "venv/",
                ".min.",
                ".pyc",
                ".pyo",
                ".pyd",
                ".so",
                ".dll",
                ".class",
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".ico",
                ".svg",
                ".ttf",
                ".woff",
                ".webp",
                "__pycache__/",
                ".cache/",
                ".tmp/",
                "yarn.lock",
                "poetry.lock",
                "*.log",
                ".vscode/",
                ".idea/",
            ]
            return not any(pattern in path.lower() for pattern in excluded_patterns)

        paths = [
            item["path"].lstrip("/")
            for item in data.get("value", [])
            if item.get("gitObjectType") == "blob" and should_include_file(item["path"])
        ]
        return "\n".join(paths)

    def get_repo_readme(self, organization: str, repo: str, project: str | None = None):
        project = project or repo
        api_url = (
            f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo}/items"
            "?path=/README.md&includeContent=true&api-version=7.0"
        )
        response = requests.get(api_url, headers=self._get_headers())
        if response.status_code == 200:
            data = response.json()
            return data.get("content", "")
        elif response.status_code == 404:
            raise ValueError("No README found for the specified repository.")
        else:
            raise Exception(
                f"Failed to fetch README: {response.status_code}, {response.text}"
            )
