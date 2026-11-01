#!/usr/bin/env python3
"""
WebHunter OS — Auto-Router

Routes user queries to the right file(s) in the webhunter-os knowledge base.

Usage:
  python3 _router.py "IDOR in REST API"
  python3 _router.py "SSRF cloud metadata"
  python3 _router.py "JWT alg confusion"
  python3 _router.py --interactive
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).parent


def scan_files():
    """Scan all .md files and extract metadata."""
    files_data = []
    for root, dirs, files in os.walk(SKILL_DIR):
        for f in files:
            if not f.endswith('.md') or f in ('INDEX.md', 'SKILL.md'):
                continue
            full_path = Path(root) / f
            rel_path = full_path.relative_to(SKILL_DIR)
            try:
                content = full_path.read_text(errors='ignore')
            except:
                continue

            m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = m.group(1).strip() if m else f.replace('.md', '').replace('_', ' ').title()
            # If first heading is generic ("WebHunter OS v1.0"), use second
            if title.lower() in ('webhunter os v1.0', 'bughunter os v1.0', 'bughunteros v1.0', 'webhunteros v1.0'):
                all_h = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)
                if len(all_h) > 1:
                    title = all_h[1].strip()

            cat = str(rel_path).split('/')[0] if '/' in str(rel_path) else 'root'

            files_data.append({
                'path': str(rel_path),
                'title': title,
                'category': cat,
                'content_sample': content[:800].lower(),
            })
    return files_data


# Keyword → file pattern mapping
KEYWORD_MAP = {
    # Auth/Authz
    'idor': ['idor', 'broken_access', 'bola', 'bfla', 'phase1-auth/IDOR', 'exploit-kb-1/Authorization'],
    'bola': ['bola', 'bfla', 'idor', 'broken_access'],
    'broken auth': ['broken_auth', 'brokenauthentication', 'phase1-auth/Broken_Authentication', 'login_testing'],
    'jwt': ['jwt', 'json web token', 'phase1-auth/JWT', 'exploit-kb-1/Authentication/JWT'],
    'oauth': ['oauth', 'oidc', 'phase1-auth', 'playbook-core/Authentication'],
    'oidc': ['oidc', 'oauth'],
    'session': ['session', 'cookie', 'phase3-session-api', 'playbook-core/Authentication'],
    'mfa': ['mfa', 'multi-factor', '2fa'],
    'password': ['password', 'credential', 'phase1-auth', 'login_testing'],
    'credential': ['credential', 'password'],

    # Injection
    'sqli': ['sql injection', 'sqli', 'phase2-injection/SQL', 'exploit-kb-1/Injection/SQLi'],
    'sql injection': ['sqli', 'sql injection', 'sql_injection'],
    'ssti': ['ssti', 'template injection', 'phase2-injection/Server_Side_Template'],
    'command injection': ['command injection', 'rce', 'phase2-injection/Command', 'exploit-kb-2/Server_Side/RCE'],
    'rce': ['rce', 'command injection', 'phase2-injection', 'exploit-kb-2/Server_Side/RCE', 'playbook-vuln/RCE'],
    'xxe': ['xxe', 'xml', 'phase2-injection'],
    'deserialization': ['deserialization', 'deserialize', 'playbook-vuln/Deserialization'],
    'mass assignment': ['mass assignment', 'mass_assignment', 'phase2-injection/Mass_Assignment', 'exploit-kb-3/API_Exposure/Mass_Assignment'],

    # Session/API
    'ssrf': ['ssrf', 'server-side request forgery', 'exploit-kb-1/Injection/SSRF'],
    'csrf': ['csrf', 'cross-site request forgery', 'phase3-session-api/07_API_Security/CSRF', 'exploit-kb-2/Browser_Security/CSRF'],
    'cors': ['cors', 'cross-origin', 'phase3-session-api/07_API_Security/CORS', 'exploit-kb-2/Browser_Security/CORS'],
    'xss': ['xss', 'cross-site scripting', 'phase4-advanced/12_Client_Side', 'exploit-kb-2/Browser_Security'],
    'prototype pollution': ['prototype pollution', 'phase4-advanced'],
    'open redirect': ['open redirect', 'phase4-advanced'],
    'graphql': ['graphql', 'phase3-session-api/07_API_Security/GraphQL', 'exploit-kb-3/API_Exposure'],
    'rest api': ['rest', 'rest_api', 'api', 'phase3-session-api/07_API_Security/REST', 'playbook-core/API'],
    'api': ['api', 'rest', 'graphql', 'phase3-session-api/07_API_Security', 'playbook-core/API'],
    'rate limit': ['rate limit', 'rate_limit', 'rate-limit', 'exploit-kb-3/API_Exposure/API_Rate_Limiting'],
    'websocket': ['websocket', 'ws://', 'phase4-advanced/12_Client_Side'],
    'http smuggling': ['smuggling', 'http request smuggling', 'phase4-advanced'],

    # File/Path
    'path traversal': ['path traversal', 'path_traversal', 'lfi', 'rfi', 'exploit-kb-2/Server_Side/Path_Traversal', 'playbook-vuln/Path_Traversal'],
    'lfi': ['lfi', 'path traversal'],
    'rfi': ['rfi', 'path traversal'],
    'file upload': ['file upload', 'file_upload', 'playbook-vuln/File_Upload'],

    # Business
    'business logic': ['business logic', 'workflow', 'phase4-advanced/16_Business_Logic'],
    'workflow bypass': ['workflow bypass', 'business logic', 'phase4-advanced/16_Business_Logic'],
    'race condition': ['race condition', 'phase4-advanced'],
    'dos': ['dos', 'denial of service', 'resource exhaustion', 'phase4-advanced/14_Denial_of_Service'],
    'redos': ['redos', 'regex dos'],
    'info disclosure': ['information disclosure', 'info disclosure', 'phase4-advanced/13_Information_Disclosure'],
    'misconfig': ['misconfig', 'security misconfiguration', 'phase4-advanced/15_Security_Misconfiguration'],

    # Cloud
    'aws': ['aws', 'amazon', 's3', 'exploit-kb-4', 'playbook-cloud'],
    'gcp': ['gcp', 'google cloud', 'exploit-kb-4'],
    'azure': ['azure', 'microsoft', 'exploit-kb-4'],
    's3': ['s3', 'bucket', 'aws'],
    'cloud': ['cloud', 'aws', 'gcp', 'azure', 'exploit-kb-4', 'playbook-cloud'],
    'iam': ['iam', 'identity', 'exploit-kb-4/IAM', 'playbook-cloud/IAM'],
    'metadata': ['metadata', 'cloud metadata', '169.254.169.254'],
    'kubernetes': ['kubernetes', 'k8s', 'exploit-kb-4'],
    'docker': ['docker', 'exploit-kb-4'],
    'ci/cd': ['ci/cd', 'ci-cd', 'cicd', 'github actions', 'exploit-kb-4/CI_CD', 'playbook-cloud/CI_CD'],
    'terraform': ['terraform', 'tfstate', 'exploit-kb-4'],
    'secrets': ['secrets', 'api keys', 'tokens', 'exploit-kb-4/Secrets', 'playbook-cloud/Secrets'],
    'nginx': ['nginx', 'reverse proxy', 'exploit-kb-4/Web_Infrastructure', 'playbook-cloud/Reverse_Proxy'],
    'reverse proxy': ['reverse proxy', 'nginx', 'apache', 'playbook-cloud/Reverse_Proxy'],

    # Tech stack
    'spa': ['spa', 'single page', 'react', 'vue', 'playbook-modern/SPA'],
    'react': ['react', 'spa', 'playbook-modern/SPA'],
    'vue': ['vue', 'spa', 'playbook-modern/SPA'],
    'angular': ['angular', 'spa', 'playbook-modern/SPA'],
    'next.js': ['next', 'nextjs', 'spa', 'playbook-modern/SPA'],
    'microservices': ['microservices', 'micro-services', 'playbook-modern/Microservices'],
    'event-driven': ['event-driven', 'event driven', 'message queue', 'kafka', 'playbook-modern/Event_Driven'],
    'api gateway': ['api gateway', 'gateway', 'playbook-modern/API_Gateway'],

    # Process
    'recon': ['recon', 'reconnaissance', 'workflow/Phase1'],
    'subdomain': ['subdomain', 'subdomain enum', 'amass', 'subfinder'],
    'dns': ['dns', 'zone transfer', 'workflow/Phase1'],
    'port scan': ['port scan', 'nmap', 'masscan'],
    'fingerprint': ['fingerprint', 'wappalyzer', 'whatweb', 'tech detect'],
    'osint': ['osint', 'open source intelligence'],
    'report': ['report', 'reporting', 'workflow/Phase8', 'reporting-quality', 'orchestrator-core/Report_Generator'],
    'remediation': ['remediation', 'fix', 'workflow/Phase8', 'reporting-quality'],
    'quality': ['quality', 'gate', 'reporting-quality/Quality_Gate'],
    'false positive': ['false positive', 'reporting-quality', 'decision-engine/Confidence_Scoring'],

    # Process - phase-based
    'phase 1': ['workflow/Phase1', 'recon'],
    'phase 2': ['workflow/Phase2', 'attack surface'],
    'phase 3': ['workflow/Phase3', 'threat model'],
    'phase 6': ['workflow/Phase6', 'exploit validation'],
    'phase 8': ['workflow/Phase8', 'reporting'],
    'start audit': ['workflow/Phase1', 'orchestrator-core/Workflow_Controller'],
    'audit web': ['workflow/Phase1', 'playbook-core'],
}


def route_query(query, files_data):
    """Route a query to relevant files."""
    query_lower = query.lower()
    matches = []

    for kw, patterns in KEYWORD_MAP.items():
        if kw in query_lower:
            for f in files_data:
                path_lower = f['path'].lower()
                title_lower = f['title'].lower()
                for p in patterns:
                    if p.lower() in path_lower or p.lower() in title_lower or p.lower() in f['content_sample']:
                        score = 10
                        if kw in title_lower:
                            score += 5
                        if kw in path_lower:
                            score += 3
                        matches.append((score, f))
                        break

    # De-duplicate
    seen = set()
    unique = []
    for score, f in sorted(matches, key=lambda x: -x[0]):
        if f['path'] not in seen:
            seen.add(f['path'])
            unique.append((score, f))

    return unique[:15]


def print_results(query, matches):
    """Print routed results."""
    print(f"\n🔍 Query: \"{query}\"\n")
    if not matches:
        print("❌ No matches. Try: idor, sqli, ssrf, jwt, xss, graphql, csrf, aws, recon, etc.\n")
        return

    print(f"📂 {len(matches)} relevant file(s):\n")
    for i, (score, f) in enumerate(matches, 1):
        print(f"  [{i}] {f['path']}")
        print(f"      → {f['title']}")
        print(f"      (category: {f['category']}, score: {score})")
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    files_data = scan_files()

    if sys.argv[1] in ('--interactive', '-i'):
        print("\n🤖 WebHunter OS Router (interactive mode)")
        print("Type 'quit' or 'exit' to stop\n")
        while True:
            try:
                query = input("🔍 Query: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not query or query.lower() in ('quit', 'exit', 'q'):
                break
            matches = route_query(query, files_data)
            print_results(query, matches)
    else:
        query = ' '.join(sys.argv[1:])
        matches = route_query(query, files_data)
        print_results(query, matches)


if __name__ == '__main__':
    main()
