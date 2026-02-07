#!/usr/bin/env python3
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import sys

GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', 'seignert.valentin@gmail.com')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')
FROM_NAME = "Newsletter Allemand"
SUBJECT_TEMPLATE = "📰 Votre newsletter quotidienne - {date}"
DESTINATAIRES = os.environ.get('DESTINATAIRES', 'seignert.valentin@gmail.com').split(',')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# ============================================================================
# FONCTION D'ENVOI
# ============================================================================

def envoyer_newsletter(html_path, destinataires=None):
    """
    Envoie la newsletter HTML par email
    
    Args:
        html_path: Chemin vers le fichier HTML
        destinataires: Liste d'emails (optionnel, utilise DESTINATAIRES par défaut)
    
    Returns:
        dict: Résultats de l'envoi
    """
    
    print("=" * 80)
    print("📧 ENVOI DE LA NEWSLETTER PAR EMAIL")
    print("=" * 80 + "\n")
    
    # 1. Charger le HTML
    print(f"📄 Chargement du fichier: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        print(f"   ✅ HTML chargé ({len(html_content)} caractères)\n")
    except FileNotFoundError:
        print(f"   ❌ Fichier non trouvé: {html_path}\n")
        return {"success": False, "error": "File not found"}
    
    # 2. Préparer la liste des destinataires
    if destinataires is None:
        destinataires = DESTINATAIRES
    
    print(f"👥 Destinataires: {len(destinataires)} personne(s)")
    for email in destinataires:
        print(f"   • {email}")
    print()
    
    # 3. Générer le sujet avec la date
    date_str = datetime.now().strftime("%d/%m/%Y")
    subject = SUBJECT_TEMPLATE.format(date=date_str)
    print(f"📬 Sujet: {subject}\n")
    
    # 4. Connexion au serveur SMTP
    print("🔐 Connexion au serveur Gmail SMTP...")
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD.replace(" ", ""))
        print("   ✅ Connexion établie\n")
    except smtplib.SMTPAuthenticationError:
        print("   ❌ Erreur d'authentification!")
        print("   💡 Vérifiez votre email et App Password\n")
        return {"success": False, "error": "Authentication failed"}
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}\n")
        return {"success": False, "error": str(e)}
    
    # 5. Envoi des emails
    print("📨 Envoi en cours...\n")
    resultats = {
        "success": True,
        "sent": 0,
        "failed": 0,
        "errors": []
    }
    
    for destinataire in destinataires:
        try:
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{FROM_NAME} <{GMAIL_ADDRESS}>"
            msg['To'] = destinataire
            msg['Subject'] = subject
            
            # Ajouter le contenu HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Envoyer
            server.send_message(msg)
            
            print(f"   ✅ Envoyé à {destinataire}")
            resultats["sent"] += 1
            
        except Exception as e:
            print(f"   ❌ Échec pour {destinataire}: {e}")
            resultats["failed"] += 1
            resultats["errors"].append({
                "email": destinataire,
                "error": str(e)
            })
    
    # 6. Fermer la connexion
    server.quit()
    print()
    
    # 7. Résumé
    print("=" * 80)
    print("✅ ENVOI TERMINÉ")
    print("=" * 80)
    print(f"\n📊 Résultats:")
    print(f"   ✅ Envoyés: {resultats['sent']}")
    print(f"   ❌ Échecs: {resultats['failed']}")
    
    if resultats['failed'] > 0:
        print(f"\n⚠️  Erreurs détaillées:")
        for error in resultats['errors']:
            print(f"   • {error['email']}: {error['error']}")
    
    print()
    return resultats


# ============================================================================
# TEST DE CONFIGURATION
# ============================================================================

def tester_configuration():
    """Teste la connexion SMTP Gmail"""
    
    print("=" * 80)
    print("🔧 TEST DE CONFIGURATION GMAIL SMTP")
    print("=" * 80 + "\n")
    
    print("📝 Configuration actuelle:")
    print(f"   Email: {GMAIL_ADDRESS}")
    print(f"   App Password: {'*' * len(GMAIL_APP_PASSWORD.replace(' ', ''))}")
    print(f"   Serveur: {SMTP_SERVER}:{SMTP_PORT}\n")
    
    print("🔐 Test de connexion...\n")
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD.replace(" ", ""))
        server.quit()
        
        print("✅ SUCCÈS! La configuration est correcte.\n")
        print("💡 Vous pouvez maintenant envoyer des newsletters!\n")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ ERREUR D'AUTHENTIFICATION\n")
        print("💡 Solutions:")
        print("   1. Vérifiez que l'email est correct")
        print("   2. Vérifiez que l'App Password est correct (16 caractères)")
        print("   3. Assurez-vous que la validation en 2 étapes est activée")
        print("   4. Créez un nouveau App Password si nécessaire\n")
        return False
        
    except Exception as e:
        print(f"❌ ERREUR: {e}\n")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Point d'entrée principal"""
    
    if len(sys.argv) < 2:
        print("\n" + "=" * 80)
        print("📧 ENVOI DE NEWSLETTER - GMAIL SMTP")
        print("=" * 80 + "\n")
        print("Usage:")
        print("  python3 send_newsletter.py <fichier.html>")
        print("\nExemples:")
        print("  python3 send_newsletter.py newsletter_20260207_123456.html")
        print("  python3 send_newsletter.py test  # Pour tester la config\n")
        print("⚠️  N'oubliez pas de configurer vos identifiants dans le script!\n")
        return
    
    # Mode test
    if sys.argv[1] == "test":
        tester_configuration()
        return
    
    # Mode envoi
    html_path = sys.argv[1]
    
    # Vérifier que la config n'est pas vide
    if GMAIL_ADDRESS == "votre.email@gmail.com" or "xxxx" in GMAIL_APP_PASSWORD:
        print("\n❌ ERREUR: Configuration non renseignée!\n")
        print("Éditez le script et modifiez:")
        print("  - GMAIL_ADDRESS (votre email)")
        print("  - GMAIL_APP_PASSWORD (votre App Password de 16 caractères)")
        print("  - DESTINATAIRES (liste d'emails pour les tests)\n")
        return
    
    # Envoyer
    resultats = envoyer_newsletter(html_path)
    
    if resultats["success"] and resultats["sent"] > 0:
        print("🎉 Newsletter envoyée avec succès!\n")
        print("💡 Vérifiez votre boîte de réception (et les spams)\n")
    else:
        print("⚠️  L'envoi a rencontré des problèmes.\n")


if __name__ == "__main__":
    main()
