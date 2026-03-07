#!/usr/bin/env python3
"""Quick test: enrich a single contact via the new Apify + Serper pipeline."""
import os, sys, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from execution.enrich_contacts import enrich_single_contact, extract_linkedin_slug, scrape_linkedin_apify

# Simulate a contact row from Supabase
test_contact = {
    'id': 'test-123',
    'name': 'Carolyn Mauricette',
    'linkedin_url': 'https://ca.linkedin.com/in/carolyn-mauricette-0438321',
    'source': 'programmer film festival site:linkedin.com',
    'bio': None,
    'email': None,
    'instagram': None,
}

print("=" * 60)
print(f"Testing slug extraction...")
slug = extract_linkedin_slug(test_contact['linkedin_url'])
print(f"  LinkedIn URL: {test_contact['linkedin_url']}")
print(f"  Extracted slug: {slug}")
print()

print("=" * 60)
print(f"Testing full enrichment for: {test_contact['name']}")
print("=" * 60)

result = enrich_single_contact(test_contact)
print()
print("=" * 60)
print("ENRICHMENT RESULT:")
print(json.dumps(result, indent=2, default=str))
