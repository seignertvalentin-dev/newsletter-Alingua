#!/usr/bin/env python3
"""
NEWSLETTER GENERATOR - PIPELINE COMPLET
Génère automatiquement une newsletter quotidienne en allemand niveau A2

Pipeline:
1. Récupération des flux RSS
2. Scoring et sélection du meilleur article
3. Extraction du contenu
4. Simplification avec LLM (Phi-3)
5. Génération HTML

Usage: python3 newsletter_pipeline.py
"""

import requests
from bs4 import BeautifulSoup
import feedparser
import warnings
import json
import re
import ssl
from datetime import datetime

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# ============================================================================
# CONFIGURATION
# ============================================================================

FLUX_RSS = [
    {
        "nom": "DW Culture",
        "url": "https://rss.dw.com/rdf/rss-de-cul",
        "score_base": 2
    },
    {
        "nom": "Tagesschau",
        "url": "https://www.tagesschau.de/xml/rss2",
        "score_base": 1
    }
]

MOTS_CLES_POSITIFS = [
    "kultur", "gesellschaft", "geschichte", "umwelt", "europa",
    "kunst", "musik", "film", "literatur", "wissenschaft"
]

MOTS_CLES_NEGATIFS = [
    "tote", "krieg", "angriff", "terror", "krise", "gewalt",
    "eilmeldung", "breaking", "live"
]

SEUIL_SELECTION = 6

# ============================================================================
# ÉTAPE 1 : RÉCUPÉRATION RSS
# ============================================================================

def recuperer_articles_rss():
    """Récupère les articles de tous les flux RSS"""
    print("=" * 80)
    print("📡 ÉTAPE 1/5 : RÉCUPÉRATION DES FLUX RSS")
    print("=" * 80 + "\n")
    
    tous_articles = []
    
    # Contournement SSL si nécessaire
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    for flux in FLUX_RSS:
        print(f"🔍 Récupération: {flux['nom']}...")
        try:
            feed = feedparser.parse(flux['url'])
            nb_articles = len(feed.entries)
            print(f"   ✅ {nb_articles} articles trouvés")
            
            for entry in feed.entries:
                article = {
                    'titre': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'source': flux['nom'],
                    'score_base': flux['score_base'],
                    'date': entry.get('published', '')
                }
                tous_articles.append(article)
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print(f"\n✅ Total: {len(tous_articles)} articles collectés\n")
    return tous_articles


# ============================================================================
# ÉTAPE 2 : SCORING ET SÉLECTION
# ============================================================================

def scorer_article(article):
    """Calcule le score d'un article"""
    score = article['score_base']
    titre_lower = article['titre'].lower()
    
    # Mots-clés positifs (+3 points)
    for mot in MOTS_CLES_POSITIFS:
        if mot in titre_lower:
            score += 3
            break
    
    # Mots-clés négatifs (-5 points)
    for mot in MOTS_CLES_NEGATIFS:
        if mot in titre_lower:
            score -= 5
            break
    
    # Longueur titre (+1 si < 80 caractères)
    if len(article['titre']) < 80:
        score += 1
    
    # Pas de breaking news (+2)
    if not any(x in titre_lower for x in ['eilmeldung', 'breaking', 'live']):
        score += 2
    
    return score


def selectionner_meilleur_article(articles):
    """Sélectionne le meilleur article selon le scoring"""
    print("=" * 80)
    print("🎯 ÉTAPE 2/5 : SCORING ET SÉLECTION")
    print("=" * 80 + "\n")
    
    # Scorer tous les articles
    articles_scores = []
    for article in articles:
        score = scorer_article(article)
        if score >= SEUIL_SELECTION:
            articles_scores.append((article, score))
    
    # Trier par score décroissant
    articles_scores.sort(key=lambda x: x[1], reverse=True)
    
    if not articles_scores:
        print("❌ Aucun article ne dépasse le seuil de sélection!")
        return None
    
    # Afficher le top 5
    print("📊 Top 5 articles:\n")
    for i, (article, score) in enumerate(articles_scores[:5], 1):
        print(f"{i}. [{score}/10] {article['titre'][:60]}...")
        print(f"   Source: {article['source']}\n")
    
    meilleur = articles_scores[0][0]
    meilleur_score = articles_scores[0][1]
    
    print(f"✅ Article sélectionné (score: {meilleur_score}/10):")
    print(f"   {meilleur['titre']}")
    print(f"   {meilleur['url']}\n")
    
    return meilleur


# ============================================================================
# ÉTAPE 3 : EXTRACTION CONTENU
# ============================================================================

def extraire_contenu_article(url):
    """Extrait le contenu textuel d'un article web"""
    print("=" * 80)
    print("📰 ÉTAPE 3/5 : EXTRACTION DU CONTENU")
    print("=" * 80 + "\n")
    
    print(f"🔍 Extraction depuis: {url[:50]}...\n")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphes = soup.find_all('p')
        texte_complet = []
        
        for p in paragraphes:
            texte = p.get_text().strip()
            if len(texte) > 30:
                texte_complet.append(texte)
        
        contenu = '\n\n'.join(texte_complet)
        contenu = contenu[:2000]
        
        print(f"✅ Contenu extrait: {len(contenu)} caractères\n")
        return contenu
    
    except Exception as e:
        print(f"❌ Erreur extraction: {e}\n")
        return None


# ============================================================================
# ÉTAPE 4 : GÉNÉRATION LLM
# ============================================================================

def generer_section_llm(texte, titre, section_type, model="phi3"):
    """Génère une section avec Ollama"""
    
    prompts = {
        "article": f"""Simplifie ce texte allemand au niveau A2.

RÈGLES STRICTES:
- Exactement 10-12 phrases
- Chaque phrase: 6-10 mots maximum
- Présent uniquement
- Vocabulaire A2 basique
- PAS de noms propres compliqués

Texte: {texte[:1200]}

Écris SEULEMENT le texte allemand simplifié (arrête après 12 phrases):""",

        "vocabulaire": f"""Extrait 5 mots allemands UTILES de ce texte (pas de noms propres).

Texte: {texte[:1000]}

Format EXACT (une ligne par mot):
1. [mot allemand] = [traduction française]
2. [mot allemand] = [traduction française]
3. [mot allemand] = [traduction française]
4. [mot allemand] = [traduction française]
5. [mot allemand] = [traduction française]

Choisis des VERBES, NOMS ou ADJECTIFS utiles.
Écris UNIQUEMENT les 5 lignes:""",

        "grammaire": f"""Trouve UNE règle de grammaire allemande simple dans ce texte.

Texte: {texte[:800]}

Explique en français en 2-3 phrases courtes et claires.
Donne un exemple simple.
Écris UNIQUEMENT l'explication en français:""",

        "resume": f"""Résume ce texte en français en 3 phrases courtes (40-60 mots total).

Texte: {texte[:1000]}

Écris UNIQUEMENT le résumé français (3 phrases):"""
    }
    
    prompt = prompts.get(section_type, "")
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 250 if section_type == "article" else 120
                }
            },
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            generated = result.get('response', '').strip()
            
            # Nettoyage
            if section_type == "article" and len(generated) > 650:
                generated = generated[:650].rsplit('.', 1)[0] + '.'
            
            return generated
        else:
            return None
            
    except Exception as e:
        print(f"   ⚠️ Erreur LLM: {e}")
        return None


def generer_newsletter_llm(contenu, titre):
    """Génère toutes les sections de la newsletter"""
    print("=" * 80)
    print("🤖 ÉTAPE 4/5 : GÉNÉRATION AVEC LLM (PHI-3)")
    print("=" * 80 + "\n")
    
    sections = {}
    
    # Article
    print("   📝 1/4 - Article simplifié (30-60s)...")
    sections['article'] = generer_section_llm(contenu, titre, "article")
    if sections['article']:
        print(f"   ✅ Généré: {len(sections['article'])} caractères")
    else:
        print("   ❌ Échec")
        return None
    
    # Vocabulaire
    print("\n   📚 2/4 - Vocabulaire (20-40s)...")
    sections['vocabulaire'] = generer_section_llm(contenu, titre, "vocabulaire")
    if sections['vocabulaire']:
        nb_mots = len([l for l in sections['vocabulaire'].split('\n') if '=' in l])
        print(f"   ✅ Généré: {nb_mots} mots")
    else:
        print("   ❌ Échec")
        return None
    
    # Grammaire
    print("\n   📖 3/4 - Point de langue (20-40s)...")
    sections['grammaire'] = generer_section_llm(contenu, titre, "grammaire")
    if sections['grammaire']:
        print(f"   ✅ Généré: {len(sections['grammaire'])} caractères")
    else:
        print("   ❌ Échec")
        return None
    
    # Résumé
    print("\n   🇫🇷 4/4 - Résumé français (20-40s)...")
    sections['resume'] = generer_section_llm(contenu, titre, "resume")
    if sections['resume']:
        print(f"   ✅ Généré: {len(sections['resume'].split())} mots")
    else:
        print("   ❌ Échec")
        return None
    
    print()
    return sections


# ============================================================================
# ÉTAPE 5 : GÉNÉRATION HTML
# ============================================================================

def generer_html(titre, sections, url_source, template_path="newsletter_template.html"):
    """Génère le HTML final"""
    print("=" * 80)
    print("🎨 ÉTAPE 5/5 : GÉNÉRATION HTML")
    print("=" * 80 + "\n")
    
    # Charger template
    print("📄 Chargement du template...")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        print("   ✅ Template chargé\n")
    except FileNotFoundError:
        print(f"   ❌ Template non trouvé: {template_path}\n")
        return None
    
    # Parser vocabulaire
    vocab_html = ""
    for ligne in sections['vocabulaire'].split('\n'):
        if '=' in ligne:
            parts = ligne.split('=', 1)
            if len(parts) == 2:
                mot = re.sub(r'^\d+\.\s*', '', parts[0]).strip()
                trad = parts[1].strip()
                vocab_html += f"""
                    <li class="vocab-item">
                        <div class="vocab-word">{mot}</div>
                        <div class="vocab-translation">= {trad}</div>
                    </li>"""
    
    # Remplacer placeholders
    print("🔧 Assemblage du HTML...")
    html = template
    replacements = {
        '{{TITRE_ARTICLE}}': titre,
        '{{ARTICLE_SIMPLIFIE}}': sections['article'].replace('\n', '<br><br>'),
        '{{VOCABULAIRE_ITEMS}}': vocab_html,
        '{{POINT_LANGUE}}': sections['grammaire'].replace('\n', '<br><br>'),
        '{{RESUME_FRANCAIS}}': sections['resume'].replace('\n', '<br><br>'),
        '{{DATE}}': datetime.now().strftime("%d/%m/%Y"),
        '{{LIEN_ARTICLE}}': url_source
    }
    
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    
    print("   ✅ HTML assemblé\n")
    
    # Sauvegarder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_filename = f"newsletter_{timestamp}.html"
    
    print(f"💾 Sauvegarde: {html_filename}")
    try:
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"   ✅ Fichier créé!\n")
        return html_filename
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
        return None


# ============================================================================
# SAUVEGARDE JSON
# ============================================================================

def sauvegarder_json(titre, sections, url_source):
    """Sauvegarde les données en JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    contenu_newsletter = f"""📰 {titre}

=== ARTICLE SIMPLIFIÉ (Niveau A2) ===
{sections['article']}

=== VOCABULAIRE UTILE ===
{sections['vocabulaire']}

=== POINT DE LANGUE ===
{sections['grammaire']}

=== RÉSUMÉ EN FRANÇAIS ===
{sections['resume']}"""
    
    data = {
        "date_generation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "titre_original": titre,
        "url_source": url_source,
        "contenu_newsletter": contenu_newsletter,
        "modele_llm": "ollama-phi3-pipeline",
        "statut": "succès"
    }
    
    filename = f"newsletter_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON sauvegardé: {filename}")
    except Exception as e:
        print(f"⚠️  Erreur JSON: {e}")


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

def main():
    """Exécute le pipeline complet"""
    print("\n" + "=" * 80)
    print("🚀 NEWSLETTER GENERATOR - PIPELINE COMPLET")
    print("=" * 80 + "\n")
    
    debut = datetime.now()
    
    # Étape 1: RSS
    articles = recuperer_articles_rss()
    if not articles:
        print("❌ Aucun article récupéré. Arrêt.")
        return
    
    # Étape 2: Sélection
    article = selectionner_meilleur_article(articles)
    if not article:
        print("❌ Aucun article sélectionné. Arrêt.")
        return
    
    # Étape 3: Extraction
    contenu = extraire_contenu_article(article['url'])
    if not contenu:
        print("❌ Impossible d'extraire le contenu. Arrêt.")
        return
    
    # Étape 4: LLM
    sections = generer_newsletter_llm(contenu, article['titre'])
    if not sections:
        print("❌ Échec de la génération LLM. Arrêt.")
        return
    
    # Étape 5: HTML
    html_file = generer_html(article['titre'], sections, article['url'])
    if not html_file:
        print("❌ Échec de la génération HTML. Arrêt.")
        return
    
    # Sauvegarde JSON
    sauvegarder_json(article['titre'], sections, article['url'])
    
    # Résumé final
    duree = (datetime.now() - debut).total_seconds()
    
    print("\n" + "=" * 80)
    print("✅ PIPELINE TERMINÉ AVEC SUCCÈS!")
    print("=" * 80)
    print(f"\n📧 Newsletter générée: {html_file}")
    print(f"⏱️  Temps total: {int(duree // 60)}m {int(duree % 60)}s")
    print(f"\n💡 Ouvrez {html_file} dans votre navigateur pour prévisualiser!")
    print("\n🎯 Prochaine étape: Envoi automatique par email (Brevo)\n")


if __name__ == "__main__":
    main()
