import os
import json


def crawl_site(siteroot: str) -> bool:
    """
        Crawls the site and saves the results to ./data.json
        Args:
            siteroot (str) root URL of the target site (example:  www.example.com)
    """
    os.system(f"""
    npx get-site-urls {siteroot} 
    """)




def audit(siteroot: str) -> bool:
    """
        Crawls the site and audits the results and saves to /agentx/temp/lighthouse/
        Args:
            siteroot (str) root URL of the target site (example:  www.example.com)
    """
    crawl_site(siteroot)
    os.makedirs('../../temp/lighthouse', exist_ok=True)
    os.makedirs('../../logs/lighthouse', exist_ok=True)

    with open('data.json', 'r') as f:
        urls = json.load(f)
        for url in urls:
            pageName = url.split('/')[-1] 
            os.system(f"""
                lighthouse {url} \
                --only-categories=performance,seo \
                --only-audits=first-contentful-paint,last-contentful-paint,first-meaningful-paint,largest-contentful-paint-element,speed-index,total-blocking-time,server-response-time,interactive,bootup-time,long-tasks,unused-images,render-blocking-resources,unminified-css,unminified-javascript,unused-css-rules,unused-javascript,uses-responsive-images,meta-description,link-text,robots.txt,render-blocking-insight,image-alt \
                --output=json \
                --output-path=../../temp/lighthouse/{pageName}.json \
                --chrome-flags="--headless"
            """)

            filter_audit(f'../../temp/lighthouse/{pageName}.json', f'../../logs/lighthouse/{pageName}.json')


def filter_audit(audit_file: str, output_file: str):
    target = audit_file
    with open(target, 'r') as site_audit_full:
        obj = json.load(site_audit_full)
        filtered_data =  obj['audits'] 
        filtered_data = {k: v for k, v in filtered_data.items() if k != 'screenshot-thumbnails'}
        with open(output_file, 'w') as filtered_file:
            json.dump(filtered_data, filtered_file, indent=2)
    return True


audit("https://palinifoundation.vercel.app")