#!/usr/bin/env python3
"""
Secrets Scanner - Сканер утечек секретов и чувствительных данных

Проверяет файлы на наличие:
- Хардкод API ключей
- Паролей в коде
- Приватных токенов
- Чувствительных путей
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Паттерны для обнаружения секретов
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{20,}["\']', 'API Key'),
    (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']+["\']', 'Password/Secret'),
    (r'(?i)(token|auth[_-]?token)\s*[=:]\s*["\'][^"\']{20,}["\']', 'Token'),
    (r'sk-[a-zA-Z0-9]{32,}', 'OpenAI API Key'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
    (r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----', 'Private Key'),
    (r'(?i)aws[_-]?(access[_-]?key|secret)[_-]?[a-z]*\s*[=:]\s*["\'][^"\']+["\']', 'AWS Credentials'),
]

# Паттерны для placeholder значений, которые нужно заменить
PLACEHOLDER_PATTERNS = [
    (r'(?i)(changeme|replace[_-]?me)', 'Placeholder Value'),
]

# Исключения для строк кода которые содержат placeholder значения только для валидации
EXCLUDED_LINES = [
    'placeholder_values',
    'if v.lower() in',
    'your_api_key',  # Разрешаем проверку на placeholder в валидаторе
]

def should_exclude_line(line: str) -> bool:
    """Проверяет нужно ли исключить строку из сканирования"""
    for exclusion in EXCLUDED_LINES:
        if exclusion in line:
            return True
    return False

def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """Сканирует файл на наличие секретов"""
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return findings
    
    for line_num, line in enumerate(lines, 1):
        # Пропускаем комментарии и импорты .env
        if line.strip().startswith('#') or 'load_dotenv' in line:
            continue
        
        # Пропускаем строки с исключениями
        if should_exclude_line(line):
            continue
        
        for pattern, secret_type in SECRET_PATTERNS:
            if re.search(pattern, line):
                findings.append((line_num, secret_type, line.strip()))
        
        for pattern, placeholder_type in PLACEHOLDER_PATTERNS:
            if re.search(pattern, line):
                findings.append((line_num, placeholder_type, line.strip()))
    
    return findings

def scan_directory(root_dir: str, exclude_dirs: List[str] = None) -> dict:
    """Сканирует директорию на наличие секретов"""
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', 'node_modules', '.venv', 'venv']
    
    results = {
        'files_scanned': 0,
        'findings': [],
        'by_severity': {'high': 0, 'medium': 0, 'low': 0}
    }
    
    root_path = Path(root_dir)
    
    for file_path in root_path.rglob('*'):
        # Пропускаем директории
        if file_path.is_dir():
            continue
        
        # Пропускаем исключенные директории
        if any(excluded in str(file_path) for excluded in exclude_dirs):
            continue
        
        # Пропускаем сам сканер
        if file_path.name == '.secrets-scanner.py':
            continue
        
        # Сканируем только текстовые файлы
        if file_path.suffix not in ['.py', '.js', '.ts', '.yaml', '.yml', '.json', '.env', '.md', '.txt']:
            continue
        
        results['files_scanned'] += 1
        findings = scan_file(file_path)
        
        for line_num, secret_type, line_content in findings:
            severity = 'high' if 'Key' in secret_type or 'Private' in secret_type else 'medium'
            results['by_severity'][severity] += 1
            
            results['findings'].append({
                'file': str(file_path.relative_to(root_path)),
                'line': line_num,
                'type': secret_type,
                'content': line_content[:100] + '...' if len(line_content) > 100 else line_content,
                'severity': severity
            })
    
    return results

def print_report(results: dict):
    """Выводит отчет о сканировании"""
    print("\n" + "=" * 60)
    print("SECRETS SCANNER REPORT")
    print("=" * 60)
    print(f"Files scanned: {results['files_scanned']}")
    print(f"Total findings: {len(results['findings'])}")
    print(f"  - High severity: {results['by_severity']['high']}")
    print(f"  - Medium severity: {results['by_severity']['medium']}")
    print(f"  - Low severity: {results['by_severity']['low']}")
    
    if results['findings']:
        print("\n" + "-" * 60)
        print("FINDINGS:")
        print("-" * 60)
        
        for finding in sorted(results['findings'], key=lambda x: x['severity'], reverse=True):
            severity_icon = '🔴' if finding['severity'] == 'high' else '🟡'
            print(f"{severity_icon} [{finding['severity'].upper()}] {finding['file']}:{finding['line']}")
            print(f"   Type: {finding['type']}")
            print(f"   Content: {finding['content']}")
            print()
    else:
        print("\n✅ No secrets detected!")
    
    print("=" * 60)

def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    print(f"Scanning directory: {root_dir}")
    results = scan_directory(root_dir)
    print_report(results)
    
    # Возвращаем код ошибки если найдены критические уязвимости
    if results['by_severity']['high'] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
