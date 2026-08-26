# -*- coding: utf-8 -*-
"""
atualizar_maturidade.py
========================
Le os dados do index.html do Dashboard de Maturidade,
calcula o resumo por area e gera resumo_maturidade.json
para o Portal OPEX (Sumario Executivo).

Uso:
  python atualizar_maturidade.py

O script procura automaticamente o index.html na mesma pasta.
"""

import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

REPO_DIR = Path(__file__).parent.resolve()
INDEX_FILE = REPO_DIR / "index.html"
RESUMO_FILE = REPO_DIR / "resumo_maturidade.json"

# Mapeamento de areas do dashboard para nomes do Portal OPEX
MAPA_AREAS = {
    'Indústria':      'industria',
    'Agrícola':       'agricola',
    'Apoio Agrícola': 'apoio_agricola',
    'Automotiva':     'automotiva',
}

def extrair_dados(html_path: Path) -> list:
    content = html_path.read_text(encoding='utf-8')
    m = re.search(r'const diagRaw = (\[.*?\]);', content, re.DOTALL)
    if not m:
        raise RuntimeError("Nao encontrei 'const diagRaw' no index.html")
    return json.loads(m.group(1))

def calcular_resumo(registros: list) -> dict:
    # Identifica todas as rodadas e pega a mais recente
    rodadas = sorted(set(r['diagnostico'] for r in registros if r.get('diagnostico')))
    ultima_rodada = rodadas[-1] if rodadas else None

    # Calcula media por area para a ultima rodada
    area_notas = defaultdict(list)
    for r in registros:
        if r.get('diagnostico') == ultima_rodada and r.get('nota') is not None:
            area = r.get('area', '')
            area_notas[area].append(float(r['nota']))

    # Media geral
    todas_notas = [n for notas in area_notas.values() for n in notas]
    media_geral = round(sum(todas_notas) / len(todas_notas) * 100, 1) if todas_notas else 0

    # Media por area (em %)
    por_area = {}
    for area, notas in area_notas.items():
        chave = MAPA_AREAS.get(area, area.lower().replace(' ', '_'))
        por_area[chave] = round(sum(notas) / len(notas) * 100, 1)

    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    return {
        'atualizado_em': agora,
        'ultima_rodada': ultima_rodada,
        'total_rodadas': len(rodadas),
        'rodadas': rodadas,
        'media_geral': media_geral,
        'por_area': por_area,
        # Atalhos diretos para o Portal OPEX
        'mat_industria': por_area.get('industria', 0),
        'mat_agricola': por_area.get('agricola', 0),
        'mat_apoio_agricola': por_area.get('apoio_agricola', 0),
        'mat_automotiva': por_area.get('automotiva', 0),
    }

def rodar_git(cmd: list):
    print(f"$ git {' '.join(cmd)}")
    r = subprocess.run(['git'] + cmd, cwd=REPO_DIR, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.strip())
    if r.returncode != 0 and r.stderr.strip(): print(r.stderr.strip())
    return r

def main():
    print("=" * 60)
    print("Gerando resumo_maturidade.json")
    print("=" * 60)

    if not INDEX_FILE.exists():
        raise FileNotFoundError(f"index.html nao encontrado em: {INDEX_FILE}")

    print(f"Lendo: {INDEX_FILE}")
    registros = extrair_dados(INDEX_FILE)
    print(f"  -> {len(registros)} registros encontrados")

    resumo = calcular_resumo(registros)
    print(f"  -> Ultima rodada: {resumo['ultima_rodada']}")
    print(f"  -> Media geral: {resumo['media_geral']}%")
    for area, val in resumo['por_area'].items():
        print(f"     {area}: {val}%")

    RESUMO_FILE.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"\nresumo_maturidade.json salvo: {RESUMO_FILE}")

    # Git commit e push
    rodar_git(['add', 'index.html', 'resumo_maturidade.json'])
    msg = f"Atualizacao maturidade - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    commit = rodar_git(['commit', '-m', msg])
    if 'nothing to commit' in (commit.stdout + commit.stderr):
        print("Nada de novo para commitar.")
        return
    rodar_git(['push', 'origin', 'main'])
    print("\nPronto! GitHub Pages atualizado.")

if __name__ == '__main__':
    main()
