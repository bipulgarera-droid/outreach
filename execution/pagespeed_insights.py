#!/usr/bin/env python3
"""
PageSpeed Insights API Integration
Fetches performance metrics from Google's PageSpeed Insights API
"""
import os
import requests
import json
import time
from typing import Optional, Dict, Any, List

# PageSpeed API endpoint and key
PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PAGESPEED_API_KEY = os.environ.get("PAGESPEED_API_KEY", "AIzaSyBSz0KCoCYy_9VSUaqVlWr-wF-BL2KdpPM")


def fetch_pagespeed_scores(url: str, strategy: str = "mobile", max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Fetch PageSpeed Insights scores for a URL.
    
    Args:
        url: The URL to analyze
        strategy: 'mobile' or 'desktop'
        max_retries: Number of retries for rate limits
    
    Returns:
        Dict with scores and metrics, or None on error
    """
    for attempt in range(max_retries):
        try:
            params = {
                "url": url,
                "key": PAGESPEED_API_KEY,
                "strategy": strategy,
                "category": ["performance", "accessibility", "best-practices", "seo"]
            }
            
            response = requests.get(PAGESPEED_API, params=params, timeout=120)
            
            # Handle rate limiting
            if response.status_code == 429:
                wait_time = (attempt + 1) * 30  # 30s, 60s, 90s
                print(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            # Extract Lighthouse categories
            lighthouse = data.get("lighthouseResult", {})
            categories = lighthouse.get("categories", {})
            audits = lighthouse.get("audits", {})
            
            # Get scores (0-100)
            scores = {
                "performance": int((categories.get("performance", {}).get("score") or 0) * 100),
                "accessibility": int((categories.get("accessibility", {}).get("score") or 0) * 100),
                "best_practices": int((categories.get("best-practices", {}).get("score") or 0) * 100),
                "seo": int((categories.get("seo", {}).get("score") or 0) * 100),
            }
            
            # Get Core Web Vitals
            metrics = {}
            
            # First Contentful Paint
            fcp = audits.get("first-contentful-paint", {})
            metrics["fcp"] = fcp.get("displayValue", "N/A")
            metrics["fcp_score"] = fcp.get("score", 0)
            
            # Largest Contentful Paint
            lcp = audits.get("largest-contentful-paint", {})
            metrics["lcp"] = lcp.get("displayValue", "N/A")
            metrics["lcp_score"] = lcp.get("score", 0)
            
            # Cumulative Layout Shift
            cls_audit = audits.get("cumulative-layout-shift", {})
            metrics["cls"] = cls_audit.get("displayValue", "N/A")
            metrics["cls_score"] = cls_audit.get("score", 0)
            
            # Total Blocking Time (replaces FID in lab data)
            tbt = audits.get("total-blocking-time", {})
            metrics["tbt"] = tbt.get("displayValue", "N/A")
            metrics["tbt_score"] = tbt.get("score", 0)
            
            # Speed Index
            si = audits.get("speed-index", {})
            metrics["speed_index"] = si.get("displayValue", "N/A")
            metrics["speed_index_score"] = si.get("score", 0)
            
            # Parse Failed Audits for Prioritization
            prioritized_audits = []
            
            # --- TIER 1 (Score 8-10) ---
            lcp_ms = lcp.get("numericValue", 0)
            if lcp_ms > 5000:
                prioritized_audits.append({"id": "lcp-critical", "title": "Load time > 5s", "description": "Mobile site takes over 5 seconds to load (LCP), causing massive visitor drop-off before engaging.", "score": 10})
            elif lcp_ms > 3000:
                prioritized_audits.append({"id": "lcp-poor", "title": "Load time > 3s", "description": "Mobile site load time is slow (LCP > 3s), which usually leads to visitors bouncing.", "score": 9})
                
            tbt_ms = tbt.get("numericValue", 0)
            if tbt_ms > 300:
                prioritized_audits.append({"id": "tbt-critical", "title": "Main thread blocked", "description": "The site freezes for hundreds of milliseconds while loading, making it feel unresponsive to taps.", "score": 9})
                
            cls_val = cls_audit.get("numericValue", 0)
            if cls_val > 0.25:
                prioritized_audits.append({"id": "cls-critical", "title": "Visual layout shift", "description": "The site layout jumps around while loading, causing users to accidentally click the wrong buttons.", "score": 8})
                
            fcp_ms = fcp.get("numericValue", 0)
            if fcp_ms > 3000:
                prioritized_audits.append({"id": "fcp-poor", "title": "Blank screen > 3s", "description": "Visitors stare at a blank white screen for over 3 seconds before seeing any content.", "score": 8})
                
            if audits.get("render-blocking-resources", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "render-blocking", "title": "Render blocking code", "description": "Heavy scripts are blocking the page from rendering properly, frustrating mobile visitors.", "score": 9})
                
            if audits.get("unused-javascript", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "unused-js", "title": "Unused Javascript bloat", "description": "The site is bogged down by unused code, slowing everything down.", "score": 8})
                
            if audits.get("uses-optimized-images", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "heavy-images", "title": "Uncompressed images", "description": "Images are heavy and uncompressed, severely slowing down mobile load times.", "score": 8})
                
            # --- TIER 2 (Score 5-7) ---
            if scores["performance"] < 50:
                prioritized_audits.append({"id": "low-perf", "title": "Poor overall performance", "description": "The overall mobile performance score is critically low, a massive red flag for Google's mobile-first indexing.", "score": 7})
                
            if audits.get("viewport", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "viewport", "title": "Not mobile optimized", "description": "The site isn't scaling properly for mobile screens.", "score": 7})
                
            if audits.get("meta-description", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "meta-desc", "title": "Missing meta description", "description": "The site is missing a meta description, so Google doesn't know how to display it in search results.", "score": 6})
                
            if audits.get("crawlable-anchors", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "uncrawlable", "title": "Uncrawlable links", "description": "Some buttons or links are coded in a way that Google's bots literally can't follow them.", "score": 6})
                
            if audits.get("dom-size", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "dom-size", "title": "Excessive DOM size", "description": "The site has an excessively bloated structure, causing sluggish scrolling.", "score": 5})
            
            # Sort by score descending and take Top 2
            prioritized_audits.sort(key=lambda x: x["score"], reverse=True)
            top_audits = prioritized_audits[:2]
            
            return {
                "url": url,
                "strategy": strategy,
                "scores": scores,
                "metrics": metrics,
                "top_audits": top_audits,
                "success": True
            }
            
        except requests.exceptions.Timeout:
            print(f"PageSpeed API timeout for {url}")
            return {"url": url, "success": False, "error": "timeout"}
        except requests.exceptions.RequestException as e:
            print(f"PageSpeed API error for {url}: {e}")
            return {"url": url, "success": False, "error": str(e)}
        except Exception as e:
            print(f"Unexpected error fetching PageSpeed for {url}: {e}")
            return {"url": url, "success": False, "error": str(e)}
    
    # All retries exhausted
    return {"url": url, "success": False, "error": "max retries exceeded"}

def fetch_screenshot(url: str, output_path: str = None) -> Optional[str]:
    """
    Fetch a screenshot using PageSpeed Insights API.
    Returns the path to the saved image file.
    """
    try:
        params = {
            "url": url,
            "key": PAGESPEED_API_KEY,
            "strategy": "desktop", # Desktop gives a wider view usually suitable for slides
            "category": ["performance"]
        }
        
        print(f"DEBUG: Requesting screenshot for {url}...")
        response = requests.get(PAGESPEED_API, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Extract screenshot data
        lighthouse = data.get("lighthouseResult", {})
        audits = lighthouse.get("audits", {})
        screenshot_audit = audits.get("final-screenshot", {})
        details = screenshot_audit.get("details", {})
        base64_data = details.get("data", "")
        
        if not base64_data:
            print("No screenshot data found in API response")
            return None
            
        # Decode base64
        import base64
        # Format is usually "data:image/jpeg;base64,....."
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
            
        image_bytes = base64.b64decode(base64_data)
        
        # Determine output path
        if not output_path:
            import urllib.parse
            domain = urllib.parse.urlparse(url).netloc.replace(".", "_")
            output_path = f"public/screenshots/homepage_{domain}.jpg"
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
        with open(output_path, "wb") as f:
            f.write(image_bytes)
            
        print(f"Screenshot saved to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error fetching screenshot: {e}")
        return None


def get_score_color(score: int) -> str:
    """Return color based on score threshold."""
    if score >= 90:
        return "green"
    elif score >= 50:
        return "orange"
    return "red"


if __name__ == "__main__":
    # Test with a sample URL
    import sys
    
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://82e.com"
    print(f"Fetching PageSpeed scores for: {test_url}")
    
    # 1. Fetch Scores
    result = fetch_pagespeed_scores(test_url, strategy="mobile")
    
    if result and result.get("success"):
        print("\n=== SCORES ===")
        scores = result["scores"]
        for key, val in scores.items():
            color = get_score_color(val)
            print(f"  {key}: {val} ({color})")
        
        print("\n=== METRICS ===")
        metrics = result["metrics"]
        for key, val in metrics.items():
            if not key.endswith("_score"):
                print(f"  {key}: {val}")
                
        print("\n=== TOP AUDITS (PRIORITIZED) ===")
        for audit in result.get("top_audits", []):
            print(f"  [{audit['score']}/10] {audit['title']}: {audit['description']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    # 2. Fetch Screenshot
    print(f"\nFetching Screenshot for: {test_url}")
    screenshot_path = fetch_screenshot(test_url)
    if screenshot_path:
        print(f"SUCCESS: Screenshot saved to {screenshot_path}")
    else:
        print("FAILED: Screenshot capture failed.")
