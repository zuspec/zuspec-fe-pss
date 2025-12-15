#!/usr/bin/env python3
"""
Grammar Audit Script for PSS 3.0
Compares PSS 3.0 BNF (Annex B) against ANTLR4 grammar files
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

def extract_bnf_rules(spec_file):
    """Extract BNF production rules from spec markdown"""
    rules = {}
    current_section = None
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        in_annex_b = False
        line_num = 0
        for line in f:
            line_num += 1
            
            # Detect Annex B start (looking for line number around 26228)
            if line_num > 26000 and 'Annex B' in line:
                in_annex_b = True
                continue
            
            # Detect section headers
            if in_annex_b:
                section_match = re.match(r'^(B\.\d+)\s+(.+)', line.strip())
                if section_match:
                    current_section = section_match.group(1) + " " + section_match.group(2)
                    continue
            
            # Stop at next Annex
            if in_annex_b and 'Annex C' in line:
                break
            
            if in_annex_b:
                # Match BNF production: rule_name ::= ...
                # Be more flexible with whitespace
                match = re.match(r'^([a-z_][a-z_0-9]*)\s*::=', line)
                if match:
                    rule_name = match.group(1)
                    rules[rule_name] = {
                        'section': current_section or 'Unknown',
                        'line': line.strip()
                    }
    
    return rules

def extract_g4_rules(g4_file):
    """Extract parser rules from ANTLR4 grammar file"""
    rules = {}
    
    with open(g4_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Match ANTLR4 parser rule: rule_name : ...
            match = re.match(r'^([a-z_][a-z_0-9]*)\s*:', line.strip())
            if match:
                rule_name = match.group(1)
                rules[rule_name] = line.strip()
    
    return rules

def main():
    repo_root = Path(__file__).parent.parent
    spec_file = repo_root / "Portable_Test_Stimulus_Standard_v3.0.md"
    parser_g4 = repo_root / "src" / "PSSParser.g4"
    expr_parser_g4 = repo_root / "src" / "PSSExprParser.g4"
    
    print("=" * 80)
    print("PSS 3.0 Grammar Audit - Work Item 1.1")
    print("=" * 80)
    print()
    
    # Extract rules
    print("Extracting BNF rules from spec...")
    bnf_rules = extract_bnf_rules(spec_file)
    print(f"  Found {len(bnf_rules)} BNF production rules")
    
    print("Extracting rules from PSSParser.g4...")
    parser_rules = extract_g4_rules(parser_g4)
    print(f"  Found {len(parser_rules)} parser rules")
    
    print("Extracting rules from PSSExprParser.g4...")
    expr_rules = extract_g4_rules(expr_parser_g4)
    print(f"  Found {len(expr_rules)} expression parser rules")
    
    all_g4_rules = {**parser_rules, **expr_rules}
    print(f"  Total ANTLR4 rules: {len(all_g4_rules)}")
    print()
    
    # Analyze coverage
    matched_rules = []
    missing_rules = []
    
    for bnf_rule in sorted(bnf_rules.keys()):
        if bnf_rule in all_g4_rules:
            matched_rules.append(bnf_rule)
        else:
            missing_rules.append((bnf_rule, bnf_rules[bnf_rule]))
    
    # Report
    coverage_pct = (len(matched_rules) / len(bnf_rules) * 100) if bnf_rules else 0
    
    print(f"Coverage: {len(matched_rules)}/{len(bnf_rules)} ({coverage_pct:.1f}%)")
    print()
    
    # Group missing rules by section
    missing_by_section = defaultdict(list)
    for rule_name, rule_info in missing_rules:
        section = rule_info['section'] or 'Unknown'
        missing_by_section[section].append(rule_name)
    
    if missing_rules:
        print("=" * 80)
        print("MISSING GRAMMAR RULES")
        print("=" * 80)
        print()
        
        for section in sorted(missing_by_section.keys()):
            print(f"{section}:")
            for rule_name in sorted(missing_by_section[section]):
                print(f"  - {rule_name}")
            print()
    else:
        print("✓ All BNF rules are represented in the grammar!")
    
    # Look for extra rules in grammar not in spec
    extra_g4_rules = set(all_g4_rules.keys()) - set(bnf_rules.keys())
    if extra_g4_rules:
        print("=" * 80)
        print("EXTRA RULES IN GRAMMAR (not in BNF)")
        print("=" * 80)
        print("These are implementation details, optimizations, or extensions:")
        print()
        for rule in sorted(extra_g4_rules)[:20]:  # Show first 20
            print(f"  - {rule}")
        if len(extra_g4_rules) > 20:
            print(f"  ... and {len(extra_g4_rules) - 20} more")
        print()
    
    # Specific PSS 3.0 features check
    print("=" * 80)
    print("PSS 3.0 SPECIFIC FEATURES CHECK")
    print("=" * 80)
    print()
    
    pss30_features = {
        'Monitor declarations': 'monitor_declaration',
        'Abstract monitors': 'abstract_monitor_declaration',
        'Monitor activities': 'monitor_activity_declaration',
        'Monitor concat': 'monitor_activity_concat_stmt',
        'Monitor eventually': 'monitor_activity_eventually_stmt',
        'Monitor overlap': 'monitor_activity_overlap_stmt',
        'Cover statement': 'cover_stmt',
        'Yield statement': 'procedural_yield_stmt',
        'Reference types': 'reference_type',
    }
    
    for feature, rule in pss30_features.items():
        status = "✓" if rule in all_g4_rules else "✗"
        print(f"{status} {feature} ({rule})")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Grammar coverage:     {coverage_pct:.1f}%")
    print(f"Matched rules:        {len(matched_rules)}")
    print(f"Missing rules:        {len(missing_rules)}")
    print(f"Extra/impl rules:     {len(extra_g4_rules)}")
    print()
    
    # Return status
    if coverage_pct >= 90:
        print("✓ Grammar coverage is GOOD (>90%)")
        return 0
    elif coverage_pct >= 70:
        print("⚠ Grammar coverage is FAIR (70-90%)")
        return 0
    else:
        print("✗ Grammar coverage is LOW (<70%)")
        return 1

if __name__ == '__main__':
    sys.exit(main())
