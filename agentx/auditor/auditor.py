import os
import json
from pathlib import Path

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent

def audit(siteroot: str) -> bool:
    """
    Audits the website and saves results
    Args:
        siteroot (str) root URL of the target site (example: www.example.com)
    """
    project_root = get_project_root()
    temp_dir = project_root / 'temp' / 'lighthouse'
    logs_dir = project_root / 'logs' / 'lighthouse'
    
    # Create directories if they don't exist
    temp_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # For now, just create a basic audit result
    audit_result = {
        'url': siteroot,
        'performance': {
            'score': 0.8,  # Example score
            'metrics': {
                'first-contentful-paint': 1.2,
                'speed-index': 2.5,
                'largest-contentful-paint': 2.8,
                'interactive': 3.5,
                'total-blocking-time': 0.2
            }
        },
        'seo': {
            'score': 0.9,  # Example score
            'metrics': {
                'meta-description': True,
                'robots-txt': True,
                'viewport': True
            }
        }
    }
    
    # Save to both temp and logs directories
    output_file = temp_dir / 'audit.json'
    log_file = logs_dir / 'audit.json'
    
    try:
        # Save to temp directory
        with open(output_file, 'w') as f:
            json.dump(audit_result, f, indent=2)
        
        # Copy to logs directory
        with open(log_file, 'w') as f:
            json.dump(audit_result, f, indent=2)
            
        print(f"Audit results saved to {output_file} and {log_file}")
        return True
        
    except Exception as e:
        print(f"Error saving audit results: {str(e)}")
        return False