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
    # Prefer https:// over http://
    if url.startswith('http://') and not url.startswith('http://localhost'):
        url = url.replace('http://', 'https://', 1)
    
    for attempt in range(max_retries):
        try:
            params = {
                "url": url,
                "key": PAGESPEED_API_KEY,
                "strategy": strategy,
                "category": ["performance", "accessibility", "best-practices", "seo"]
            }
            
            response = requests.get(PAGESPEED_API, params=params, timeout=120)
            
            # If https:// fails with 400, try http:// as fallback
            if response.status_code == 400 and url.startswith('https://'):
                fallback_url = url.replace('https://', 'http://', 1)
                print(f"HTTPS failed for {url}, trying HTTP fallback: {fallback_url}")
                params["url"] = fallback_url
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
                lcp_sec = round(lcp_ms / 1000, 1)
                prioritized_audits.append({"id": "lcp-critical", "title": "Slow mobile load time", "description": f"The site takes around {lcp_sec} seconds to load on mobile, so most visitors leave before they even see your content.", "metric": f"{lcp_sec}s load time", "expert_term": "high Largest Contentful Paint", "score": 10})
            elif lcp_ms > 3000:
                lcp_sec = round(lcp_ms / 1000, 1)
                prioritized_audits.append({"id": "lcp-poor", "title": "Slow mobile load time", "description": f"The site takes around {lcp_sec} seconds to load on phones, which often means visitors leave before the page finishes loading.", "metric": f"{lcp_sec}s load time", "expert_term": "slow Largest Contentful Paint", "score": 9})
                
            tbt_ms = tbt.get("numericValue", 0)
            if tbt_ms > 300:
                tbt_display = f"{int(tbt_ms)}ms"
                prioritized_audits.append({"id": "tbt-critical", "title": "Site freezes on mobile", "description": f"The site freezes for about {tbt_display} while loading on phones, so visitors can't tap or scroll for a noticeable moment.", "metric": f"{tbt_display} freeze", "expert_term": "main-thread blocking", "score": 9})
                
            cls_val = cls_audit.get("numericValue", 0)
            if cls_val > 0.25:
                prioritized_audits.append({"id": "cls-critical", "title": "Content jumps around", "description": "Elements on the page shift around while loading, which can cause visitors to accidentally tap the wrong thing.", "score": 8})
                
            fcp_ms = fcp.get("numericValue", 0)
            if fcp_ms > 3000:
                fcp_sec = round(fcp_ms / 1000, 1)
                prioritized_audits.append({"id": "fcp-poor", "title": "Blank screen on load", "description": f"Visitors see a blank white screen for about {fcp_sec} seconds before anything appears, which usually makes them hit the back button.", "metric": f"{fcp_sec}s blank screen", "expert_term": "delayed First Contentful Paint", "score": 8})
                
            if audits.get("render-blocking-resources", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "render-blocking", "title": "Slow page rendering", "description": "The site has render-blocking scripts that delay the page from appearing, keeping visitors waiting longer than they should.", "metric": "render-blocking scripts detected", "expert_term": "render-blocking resources", "score": 9})
                
            if audits.get("unused-javascript", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "unused-js", "title": "Excess code slowing things down", "description": "The site is carrying unused JavaScript bundles that slow everything down for no reason.", "metric": "unused JavaScript detected", "expert_term": "unused JavaScript bundles", "score": 8})
                
            if audits.get("uses-optimized-images", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "heavy-images", "title": "Heavy images", "description": "The images on the site are unoptimized and larger than they need to be, which makes pages load noticeably slower on mobile.", "metric": "unoptimized images", "expert_term": "unoptimized image assets", "score": 8})
                
            # --- TIER 2 (Score 5-7) ---
            if scores["performance"] < 50:
                perf_display = int(scores["performance"])
                prioritized_audits.append({"id": "low-perf", "title": "Low mobile performance", "description": f"The overall mobile performance score is {perf_display}/100, which can hurt how Google ranks the site in search results.", "metric": f"{perf_display}/100 performance score", "expert_term": "low Core Web Vitals score", "score": 7})
                
            if audits.get("viewport", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "viewport", "title": "Not mobile friendly", "description": "The site doesn't adapt properly to phone screens, so visitors have to pinch and zoom to read anything.", "score": 7})
                
            if audits.get("meta-description", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "meta-desc", "title": "Missing search description", "description": "The site is missing the short summary that shows up in Google search results, so potential visitors don't know what to expect.", "score": 6})
                
            if audits.get("crawlable-anchors", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "uncrawlable", "title": "Hidden links from Google", "description": "Some links on the site are set up in a way that Google can't follow them, meaning those pages might not show up in search.", "score": 6})
                
            if audits.get("dom-size", {}).get("score", 1) < 0.9:
                prioritized_audits.append({"id": "dom-size", "title": "Overly complex page", "description": "The page structure is overly complex, which makes scrolling feel sluggish on phones.", "score": 5})
            
            # Sort by score descending and take Top 5
            prioritized_audits.sort(key=lambda x: x["score"], reverse=True)
            top_audits = prioritized_audits[:5]
            
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
