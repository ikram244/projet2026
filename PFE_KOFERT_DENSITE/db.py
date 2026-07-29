import mysql.connector
from mysql.connector import Error
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    """
    Établit une connexion à la base de données MySQL kofert_db
    Utilisateur: root, Mot de passe: (vide)
    """
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',        # WampServer utilise localhost
            port=3306,                # Port par défaut de MySQL
            database='kofert_db',     # Votre base de données
            user='root',              # Utilisateur par défaut Wamp
            password='',              # Pas de mot de passe par défaut
            charset='utf8mb4',        # Pour supporter l'unicode
            use_pure=True             # Utilise l'implémentation pure Python
        )
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            logger.info(f"✅ Connexion réussie à MySQL (Version: {db_info})")
            logger.info(f"📊 Base de données: kofert_db")
            return connection
            
    except Error as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        logger.error("Vérifiez que WampServer est démarré et MySQL est en cours d'exécution")
        return None
    
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
        return None

def test_connection():
    """Fonction de test pour vérifier la connexion"""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"✅ Connecté à la base: {db_name}")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 Tables trouvées: {len(tables)}")
            for table in tables:
                print(f"   - {table[0]}")
            
            cursor.close()
            conn.close()
            return True
        except Error as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    return False

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Exécute une requête SQL avec gestion automatique de la connexion
    
    Args:
        query: Requête SQL
        params: Paramètres pour la requête (tuple)
        fetch_one: Retourner un seul résultat
        fetch_all: Retourner tous les résultats
    
    Returns:
        Résultat de la requête ou None en cas d'erreur
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid if cursor.lastrowid else True
        
        return result
        
    except Error as e:
        logger.error(f"❌ Erreur SQL: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_user_by_email(email):
    """Récupère un utilisateur par son email"""
    query = "SELECT * FROM utilisateurs WHERE email = %s"
    return execute_query(query, (email,), fetch_one=True)

def get_user_by_id(user_id):
    """Récupère un utilisateur par son ID"""
    query = "SELECT * FROM utilisateurs WHERE id = %s"
    return execute_query(query, (user_id,), fetch_one=True)

def create_user(nom, prenom, email, mot_de_passe_hash, role):
    """Crée un nouvel utilisateur"""
    query = """
        INSERT INTO utilisateurs (nom, prenom, email, mot_de_passe, role)
        VALUES (%s, %s, %s, %s, %s)
    """
    return execute_query(query, (nom, prenom, email, mot_de_passe_hash, role))

def update_last_connexion(user_id):
    """Met à jour la date de dernière connexion"""
    query = "UPDATE utilisateurs SET last_connexion = NOW() WHERE id = %s"
    return execute_query(query, (user_id,))

# Test rapide si exécuté directement
if __name__ == "__main__":
    print("🔍 Test de connexion à la base de données...")
    print("=" * 50)
    
    if test_connection():
        print("\n✅ Tous les tests sont réussis !")
        print("✅ Votre fichier db.py est correctement configuré.")
    else:
        print("\n❌ Échec des tests. Vérifiez que WampServer est démarré.")
        print("   - Vérifiez que l'icône Wamp est verte dans la barre des tâches")
        print("   - Vérifiez que MySQL est en cours d'exécution")

def create_conversation(utilisateur_id, titre="Nouvelle conversation"):
    """Crée une nouvelle conversation et retourne son id"""
    query = "INSERT INTO conversations_chatbot (utilisateur_id, titre) VALUES (%s, %s)"
    return execute_query(query, (utilisateur_id, titre))


def get_conversations(utilisateur_id):
    """Liste les conversations d'un utilisateur, les plus récentes en premier"""
    query = """
        SELECT id, titre, date FROM conversations_chatbot
        WHERE utilisateur_id = %s ORDER BY date DESC
    """
    return execute_query(query, (utilisateur_id,), fetch_all=True)


def get_messages(conversation_id):
    """Récupère tous les messages d'une conversation, dans l'ordre"""
    query = """
        SELECT expediteur, contenu, date FROM messages_chatbot
        WHERE conversation_id = %s ORDER BY date ASC
    """
    return execute_query(query, (conversation_id,), fetch_all=True)


def add_message(conversation_id, expediteur, contenu):
    """Ajoute un message (expediteur = 'user' ou 'bot')"""
    query = """
        INSERT INTO messages_chatbot (conversation_id, expediteur, contenu)
        VALUES (%s, %s, %s)
    """
    return execute_query(query, (conversation_id, expediteur, contenu))


def update_titre_conversation(conversation_id, titre):
    """Met a jour le titre d'une conversation (ex: a partir du premier message)"""
    query = "UPDATE conversations_chatbot SET titre = %s WHERE id = %s"
    return execute_query(query, (titre, conversation_id))

def delete_conversation(conversation_id):
    """Supprime une conversation (les messages sont supprimes en cascade)"""
    query = "DELETE FROM conversations_chatbot WHERE id = %s"
    return execute_query(query, (conversation_id,))

def create_connaissance(utilisateur_id, categorie, titre, contenu, mots_cles=None):
    """Cree une nouvelle entree dans la base de connaissance du chatbot"""
    query = """
        INSERT INTO base_connaissance (utilisateur_id, categorie, titre, contenu, mots_cles)
        VALUES (%s, %s, %s, %s, %s)
    """
    return execute_query(query, (utilisateur_id, categorie, titre, contenu, mots_cles))


def get_connaissances():
    """Liste toutes les entrees, les plus recentes en premier"""
    query = """
        SELECT bc.id, bc.categorie, bc.titre, bc.contenu, bc.mots_cles,
               bc.date_creation, bc.date_modification,
               u.nom, u.prenom
        FROM base_connaissance bc
        JOIN utilisateurs u ON u.id = bc.utilisateur_id
        ORDER BY bc.date_creation DESC
    """
    return execute_query(query, fetch_all=True)


def update_connaissance(connaissance_id, categorie, titre, contenu, mots_cles=None):
    """Met a jour une entree existante"""
    query = """
        UPDATE base_connaissance
        SET categorie=%s, titre=%s, contenu=%s, mots_cles=%s
        WHERE id=%s
    """
    return execute_query(query, (categorie, titre, contenu, mots_cles, connaissance_id))


def delete_connaissance(connaissance_id):
    """Supprime une entree"""
    query = "DELETE FROM base_connaissance WHERE id = %s"
    return execute_query(query, (connaissance_id,))


def get_all_connaissances_texte():
    """Retourne toutes les entrees (categorie, titre, contenu) pour injection dans le chatbot"""
    query = "SELECT categorie, titre, contenu FROM base_connaissance ORDER BY date_creation DESC"
    return execute_query(query, fetch_all=True)