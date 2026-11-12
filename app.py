import os, json, random, hashlib, time, re, secrets
from urllib.parse import urlparse, parse_qs
from datetime import datetime, date, timedelta, timezone
from functools import wraps
from flask import Flask, current_app, render_template, request, redirect, url_for, flash, jsonify, abort, session, has_app_context
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm, CSRFProtect
from flask_migrate import Migrate
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from curriculum_data import CURRICULUM, QUESTION_BANK
from phase6_question_bank import PHASE6_QUESTIONS
from phase6_exercises import PHASE6_EXERCISES
from phase6_lesson_enrichment import enrich_theory
from phase8_lesson_content import PHASE8_DETAILS, CODE_EXAMPLES, WHY_IT_MATTERS
from content_quality import audit_lesson, split_lesson_sections, LEVELS as EXERCISE_LEVELS
from exercise_grading import ai_grading_configured, evaluate_open_answer, short_answer_matches

db=SQLAlchemy()
login_manager=LoginManager()
csrf=CSRFProtect()
migrate=Migrate()

def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)

def create_app(test_config=None):
    app=Flask(__name__)
    app.config["SECRET_KEY"]=os.environ.get("SECRET_KEY")
    if test_config: app.config.update(test_config)
    app_env=os.environ.get("APP_ENV","development").strip().lower()
    if not app.config["SECRET_KEY"]:
        if app_env in {"development","dev"}:
            # Local-only ephemeral key: avoids a hard-coded fallback and keeps
            # development startup convenient. Sessions reset when the process restarts.
            app.config["SECRET_KEY"]=secrets.token_hex(32)
            app.logger.info("Using an ephemeral development SECRET_KEY; set SECRET_KEY to persist local sessions across restarts.")
        else:
            raise RuntimeError("Set SECRET_KEY before starting InfoConcours outside development")
    default_db_url="sqlite:///infoconcours-phase8-dev.db" if app_env in {"development","dev"} else None
    db_url=os.environ.get("DATABASE_URL") or default_db_url
    if not db_url:
        raise RuntimeError("Set DATABASE_URL before starting InfoConcours outside development")
    if db_url.startswith("postgres://"): db_url=db_url.replace("postgres://","postgresql://",1)
    if db_url.startswith("postgresql://"): db_url=db_url.replace("postgresql://","postgresql+psycopg://",1)
    app.config["SQLALCHEMY_DATABASE_URI"]=db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
    app.config["SESSION_COOKIE_HTTPONLY"]=True
    app.config["SESSION_COOKIE_SAMESITE"]="Lax"
    app.config["SESSION_COOKIE_SECURE"]=os.environ.get("COOKIE_SECURE","1" if os.environ.get("APP_ENV","").lower()=="production" else "0")=="1"
    app.config["SESSION_COOKIE_NAME"]="infoconcours_session"
    app.config["REMEMBER_COOKIE_HTTPONLY"]=True
    app.config["REMEMBER_COOKIE_SAMESITE"]="Lax"
    app.config["REMEMBER_COOKIE_SECURE"]=app.config["SESSION_COOKIE_SECURE"]
    app.config["SQLALCHEMY_ENGINE_OPTIONS"]={"pool_pre_ping":True}
    app.config["ADAPTIVE_THRESHOLDS"]=[40,60,75,90]
    configured_thresholds=os.environ.get("ADAPTIVE_THRESHOLDS")
    if configured_thresholds:
        try:
            parsed=[int(value) for value in configured_thresholds.split(",")]
            if len(parsed)==4 and parsed==sorted(set(parsed)) and all(1<=value<=99 for value in parsed):
                app.config["ADAPTIVE_THRESHOLDS"]=parsed
        except ValueError:
            pass
    try: exam_minutes=int(os.environ.get("EXAM_DURATION_MINUTES","240"))
    except ValueError: exam_minutes=240
    app.config["EXAM_DURATION_MINUTES"]=max(5,min(240,exam_minutes))
    app.config["AUTO_CREATE_SCHEMA"]=os.environ.get("AUTO_CREATE_SCHEMA","1" if app_env in {"development","dev"} else "0")=="1"
    db.init_app(app); login_manager.init_app(app); csrf.init_app(app)
    migrate.init_app(app,db,compare_type=True)
    app.jinja_env.filters["fromjson"] = json.loads
    login_manager.login_view="login"
    login_manager.session_protection="strong"
    login_manager.login_message="Connecte-toi pour accéder à ton espace."
    register_routes(app)
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options","nosniff")
        response.headers.setdefault("Referrer-Policy","strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options","SAMEORIGIN")
        response.headers.setdefault("Permissions-Policy","camera=(), microphone=(), geolocation=()")
        if os.environ.get("APP_ENV","").lower()=="production" and app.config["SESSION_COOKIE_SECURE"]:
            response.headers.setdefault("Strict-Transport-Security","max-age=31536000; includeSubDomains")
        return response
    if app.config["AUTO_CREATE_SCHEMA"]:
        with app.app_context(): db.create_all()
    return app

@login_manager.user_loader
def load_user(user_id): return db.session.get(User,int(user_id))

class User(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(40),unique=True,nullable=False)
    email=db.Column(db.String(120),unique=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False)
    role=db.Column(db.String(15),default="student",nullable=False)
    created_at=db.Column(db.DateTime,default=utcnow)
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)

class Diagnostic(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    scores=db.Column(db.Text,nullable=False)
    total=db.Column(db.Integer,nullable=False)
    created_at=db.Column(db.DateTime,default=utcnow)

class StudySession(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    domain=db.Column(db.String(80),nullable=False)
    minutes=db.Column(db.Integer,nullable=False)
    studied_on=db.Column(db.Date,default=date.today,index=True)

class StudyGoal(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,unique=True,index=True)
    daily_minutes=db.Column(db.Integer,nullable=False,default=60)
    updated_at=db.Column(db.DateTime,default=utcnow,onupdate=utcnow)

class Attempt(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    mode=db.Column(db.String(20),nullable=False)
    score=db.Column(db.Integer,nullable=False)
    total=db.Column(db.Integer,nullable=False)
    details=db.Column(db.Text,default="[]")
    duration_minutes=db.Column(db.Integer,default=0)
    created_at=db.Column(db.DateTime,default=utcnow)

class LessonProgress(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    lesson_key=db.Column(db.String(100),nullable=False)
    evidence_count=db.Column(db.Integer,default=0,nullable=False)
    updated_at=db.Column(db.DateTime,default=utcnow,onupdate=utcnow)
    __table_args__=(db.UniqueConstraint("user_id","lesson_key",name="uq_lesson_progress_user_lesson"),)

class Bookmark(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    question_id=db.Column(db.Integer,db.ForeignKey("question.id"),nullable=False,index=True)
    created_at=db.Column(db.DateTime,default=utcnow)
    __table_args__=(db.UniqueConstraint("user_id","question_id",name="uq_bookmark_user_question"),)

class AuthThrottle(db.Model):
    key=db.Column(db.String(64),primary_key=True)
    window_started=db.Column(db.DateTime,nullable=False,default=utcnow)
    attempts=db.Column(db.Integer,nullable=False,default=0)

class VideoResource(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    channel=db.Column(db.String(160),nullable=False)
    video_id=db.Column(db.String(11),unique=True,nullable=False)
    language=db.Column(db.String(20),nullable=False,default="Français")
    lesson_key=db.Column(db.String(100),nullable=False,index=True)
    duration_minutes=db.Column(db.Integer)
    verified=db.Column(db.Boolean,nullable=False,default=False)
    verification_status=db.Column(db.String(24),nullable=False,default="pending",index=True)
    verified_at=db.Column(db.DateTime)
    active=db.Column(db.Boolean,nullable=False,default=True)
    created_by=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime,default=utcnow)

class VideoWatch(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    video_id=db.Column(db.Integer,db.ForeignKey("video_resource.id"),nullable=False,index=True)
    watched_at=db.Column(db.DateTime,default=utcnow)
    __table_args__=(db.UniqueConstraint("user_id","video_id",name="uq_video_watch_user_video"),)

class CurriculumSubject(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    slug=db.Column(db.String(100),unique=True,nullable=False)
    name=db.Column(db.String(100),unique=True,nullable=False)
    category=db.Column(db.String(60),nullable=False)
    weight=db.Column(db.Integer,nullable=False)
    position=db.Column(db.Integer,nullable=False,default=0)
    published=db.Column(db.Boolean,nullable=False,default=True)

class CurriculumModule(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    subject_id=db.Column(db.Integer,db.ForeignKey("curriculum_subject.id",ondelete="CASCADE"),nullable=False,index=True)
    title=db.Column(db.String(160),nullable=False)
    position=db.Column(db.Integer,nullable=False,default=0)
    published=db.Column(db.Boolean,nullable=False,default=True)

class CurriculumChapter(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    module_id=db.Column(db.Integer,db.ForeignKey("curriculum_module.id",ondelete="CASCADE"),nullable=False,index=True)
    title=db.Column(db.String(160),nullable=False)
    position=db.Column(db.Integer,nullable=False,default=0)
    published=db.Column(db.Boolean,nullable=False,default=True)

class CurriculumLesson(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    chapter_id=db.Column(db.Integer,db.ForeignKey("curriculum_chapter.id",ondelete="CASCADE"),nullable=False,index=True)
    title=db.Column(db.String(200),nullable=False)
    objectives_fr=db.Column(db.Text,nullable=False,default="[]")
    prerequisites_fr=db.Column(db.Text,nullable=False,default="")
    theory_fr=db.Column(db.Text,nullable=False,default="")
    theory_ar=db.Column(db.Text,nullable=False,default="")
    example_fr=db.Column(db.Text,nullable=False,default="")
    code_example=db.Column(db.Text,nullable=False,default="")
    exercise_fr=db.Column(db.Text,nullable=False,default="")
    solution_fr=db.Column(db.Text,nullable=False,default="")
    summary_fr=db.Column(db.Text,nullable=False,default="")
    revision_fr=db.Column(db.Text,nullable=False,default="")
    published=db.Column(db.Boolean,nullable=False,default=True)

class CourseExercise(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    lesson_id=db.Column(db.Integer,db.ForeignKey("curriculum_lesson.id",ondelete="CASCADE"),nullable=False,index=True)
    title=db.Column(db.String(180),nullable=False)
    prompt_fr=db.Column(db.Text,nullable=False)
    prompt_ar=db.Column(db.Text,nullable=False,default="")
    solution_fr=db.Column(db.Text,nullable=False)
    solution_ar=db.Column(db.Text,nullable=False,default="")
    exercise_type=db.Column(db.String(20),nullable=False,default="open")
    options_json=db.Column(db.Text,nullable=False,default="[]")
    correct_answer=db.Column(db.String(500))
    accepted_answers_json=db.Column(db.Text,nullable=False,default="[]")
    feedback_fr=db.Column(db.Text,nullable=False,default="")
    grading_guide_fr=db.Column(db.Text,nullable=False,default="")
    learning_objective_fr=db.Column(db.String(400),nullable=False,default="")
    level=db.Column(db.String(20),nullable=False,default="Moyen")
    published=db.Column(db.Boolean,nullable=False,default=True)

class ExerciseAttempt(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    exercise_id=db.Column(db.Integer,db.ForeignKey("course_exercise.id",ondelete="CASCADE"),nullable=False,index=True)
    submitted_answer=db.Column(db.Text,nullable=False)
    score=db.Column(db.Float)
    feedback=db.Column(db.Text,nullable=False,default="")
    status=db.Column(db.String(24),nullable=False,index=True)
    created_at=db.Column(db.DateTime,nullable=False,default=utcnow,index=True)
    evaluated_by=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    evaluated_at=db.Column(db.DateTime)

class LessonCompletion(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    lesson_id=db.Column(db.Integer,db.ForeignKey("curriculum_lesson.id",ondelete="CASCADE"),nullable=False,index=True)
    completed_at=db.Column(db.DateTime,nullable=False,default=utcnow)
    __table_args__=(db.UniqueConstraint("user_id","lesson_id",name="uq_lesson_completion_user_lesson"),)

class QuestionMetadata(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    question_id=db.Column(db.Integer,db.ForeignKey("question.id",ondelete="CASCADE"),unique=True,nullable=False,index=True)
    chapter_id=db.Column(db.Integer,db.ForeignKey("curriculum_chapter.id",ondelete="SET NULL"),nullable=True,index=True)
    lesson_id=db.Column(db.Integer,db.ForeignKey("curriculum_lesson.id",ondelete="SET NULL"),nullable=True,index=True)
    time_limit_seconds=db.Column(db.Integer)
    learning_objective=db.Column(db.String(400),nullable=False,default="")

class VideoMetadata(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    video_id=db.Column(db.Integer,db.ForeignKey("video_resource.id",ondelete="CASCADE"),unique=True,nullable=False,index=True)
    description=db.Column(db.Text,nullable=False,default="")
    chapter_id=db.Column(db.Integer,db.ForeignKey("curriculum_chapter.id",ondelete="SET NULL"),nullable=True,index=True)
    lesson_id=db.Column(db.Integer,db.ForeignKey("curriculum_lesson.id",ondelete="SET NULL"),nullable=True,index=True)
    thumbnail_url=db.Column(db.String(500))

class UserPreference(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),unique=True,nullable=False,index=True)
    language=db.Column(db.String(2),nullable=False,default="fr")

class CurriculumSeedState(db.Model):
    subject_slug=db.Column(db.String(100),primary_key=True)
    seeded_at=db.Column(db.DateTime,nullable=False,default=utcnow)

class Question(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    domain=db.Column(db.String(80),nullable=False,index=True)
    topic=db.Column(db.String(120),nullable=False)
    level=db.Column(db.String(20),nullable=False)
    prompt_fr=db.Column(db.Text,nullable=False)
    prompt_ar=db.Column(db.Text,nullable=False)
    options_fr=db.Column(db.Text,nullable=False)
    options_ar=db.Column(db.Text,nullable=False)
    answer=db.Column(db.Integer,nullable=False)
    explanation_fr=db.Column(db.Text,nullable=False)
    explanation_ar=db.Column(db.Text,nullable=False)
    active=db.Column(db.Boolean,default=True)

DOMAINS=[
 ("Algorithmique",20,"Développement"),("Programmation",10,"Développement"),("Bases de données",15,"Développement"),
 ("Systèmes",10,"Systèmes et réseaux"),("Réseaux",10,"Systèmes et réseaux"),("Architecture",10,"Systèmes et réseaux"),
 ("Bureautique",15,"Logiciels"),("Multimédia",10,"Logiciels")]
SEED_TOPIC_CHAPTERS={
    ("Algorithmique","Complexité"):"Récursivité, piles et complexité",("Algorithmique","Graphes"):"Récursivité, piles et complexité",
    ("Programmation","POO"):"Classes et objets",("Programmation","Python"):"Types, contrôle et fonctions",
    ("Bases de données","SQL"):"SQL : filtrer et joindre",("Bases de données","Transactions"):"Transactions et index",
    ("Systèmes","Linux"):"Fichiers, permissions et commandes",("Systèmes","OS"):"Processus et ordonnancement",("Systèmes","Processus"):"Processus et ordonnancement",
    ("Réseaux","Adressage"):"IPv4 et sous-réseaux",("Réseaux","OSI"):"Modèles en couches",("Réseaux","Services"):"DNS, DHCP et Web",
    ("Architecture","CPU"):"Cycle d’exécution et composants CPU",("Architecture","Mémoire"):"Hiérarchie mémoire",("Architecture","Unité de calcul"):"Cycle d’exécution et composants CPU",
    ("Bureautique","Analyse"):"Analyse de données",("Bureautique","Excel"):"Formules et références",
    ("Multimédia","Audio"):"Échantillonnage sonore",("Multimédia","Image"):"Formats matriciels et vectoriels",
}
SEED=[
("Algorithmique","Complexité","Facile","Quelle structure répète un bloc tant qu’une condition est vraie ?","شنو البنية اللي كتعاود التعليمات مادام الشرط صحيح؟",["if","while","switch","return"],["if","while","switch","return"],1,"while répète le bloc tant que la condition reste vraie.","while كتعاود التعليمات مادام الشرط صحيح."),
("Algorithmique","Complexité","Moyen","Quelle est la complexité d’une recherche dichotomique dans un tableau trié ?","شنو التعقيد ديال البحث الثنائي فجدول مرتب؟",["O(1)","O(log n)","O(n)","O(n²)"],["O(1)","O(log n)","O(n)","O(n²)"],1,"La recherche dichotomique divise l’espace de recherche par deux.","البحث الثنائي كيقسم مجال البحث على جوج فكل مرحلة."),
("Algorithmique","Graphes","Difficile","Quel algorithme calcule les plus courts chemins avec des poids non négatifs ?","شنو الخوارزمية اللي كتحسب أقصر المسارات بأوزان غير سالبة؟",["DFS","Kruskal","Dijkstra","Tri fusion"],["DFS","Kruskal","Dijkstra","Tri fusion"],2,"Dijkstra est adapté aux poids non négatifs.","Dijkstra كتخدم مع الأوزان غير السالبة."),
("Programmation","Python","Facile","Quel mot-clé déclare une fonction en Python ?","بأي كلمة كنعلنو على function فـ Python؟",["func","def","function","void"],["func","def","function","void"],1,"Une fonction Python se déclare avec def.","فـ Python كنستعملو def لتعريف الدالة."),
("Programmation","POO","Moyen","Quel principe permet à une sous-classe de redéfinir une méthode héritée ?","شنو المبدأ اللي كيخلي class فرعية تعاود تعريف method موروثة؟",["Encapsulation","Redéfinition","Compilation","Sérialisation"],["Encapsulation","Redéfinition","Compilation","Sérialisation"],1,"La redéfinition adapte le comportement hérité.","Redéfinition كتبدل سلوك method الموروثة."),
("Programmation","Python","Difficile","Quel type Python est immuable ?","شنو النوع فـ Python اللي مايمكنش تبدل المحتوى ديالو؟",["list","dict","tuple","set"],["list","dict","tuple","set"],2,"Un tuple ne peut pas être modifié après sa création.","tuple مايمكنش تبدل العناصر ديالو من بعد الإنشاء."),
("Bases de données","SQL","Facile","Quel langage interroge les bases relationnelles ?","شنو اللغة اللي كنستعملو للاستعلام على قواعد البيانات العلائقية؟",["HTML","SQL","CSS","XML"],["HTML","SQL","CSS","XML"],1,"SQL sert à manipuler et interroger les données.","SQL كتستعمل للتعامل مع البيانات والاستعلام عليها."),
("Bases de données","SQL","Moyen","Quelle clause filtre les lignes avant le regroupement ?","شنو clause اللي كتفلتر السطور قبل GROUP BY؟",["ORDER BY","HAVING","WHERE","GROUP BY"],["ORDER BY","HAVING","WHERE","GROUP BY"],2,"WHERE filtre les lignes avant le regroupement.","WHERE كتفلتر السطور قبل التجميع."),
("Bases de données","Transactions","Difficile","Quelle propriété ACID garantit qu’une transaction est tout ou rien ?","شنو خاصية ACID اللي كتضمن العملية إما كاملة أو تتلغى كاملة؟",["Atomicité","Cohérence","Isolation","Durabilité"],["Atomicité","Cohérence","Isolation","Durabilité"],0,"L’atomicité garantit l’exécution complète ou l’annulation.","Atomicité كتضمن العملية تكمل كاملة ولا تتلغى."),
("Systèmes","OS","Facile","Quel composant gère le processeur et la mémoire ?","شكون كيسير المعالج والذاكرة؟",["Navigateur","Système d’exploitation","Routeur","Éditeur"],["المتصفح","نظام التشغيل","الراوتر","محرر"],1,"Le système d’exploitation gère les ressources matérielles.","نظام التشغيل كيسير موارد الحاسوب."),
("Systèmes","Linux","Moyen","Quelle commande Linux affiche le répertoire courant ?","شنو أمر Linux اللي كيعرض المجلد الحالي؟",["ls","pwd","cd","mkdir"],["ls","pwd","cd","mkdir"],1,"pwd affiche le chemin courant.","pwd كيعرض المسار الحالي."),
("Systèmes","Processus","Difficile","Quel état indique qu’un processus attend un événement ?","شنو الحالة اللي كتعني أن process كيتسنى حدث؟",["Running","Ready","Blocked","Terminated"],["كيخدم","واجد","محظور","سالا"],2,"Un processus bloqué attend une ressource ou un événement.","process محظور كيتسنى مورد أو حدث."),
("Réseaux","OSI","Facile","Combien de couches compte le modèle OSI ?","شحال من طبقة فـ OSI؟",["4","5","7","8"],["4","5","7","8"],2,"Le modèle OSI comporte sept couches.","OSI فيه سبعة ديال الطبقات."),
("Réseaux","Services","Moyen","Quel service traduit un nom de domaine en adresse IP ?","شنو الخدمة اللي كتحول اسم الموقع لعنوان IP؟",["DHCP","DNS","FTP","SMTP"],["DHCP","DNS","FTP","SMTP"],1,"DNS résout les noms de domaine en adresses IP.","DNS كتحول أسماء المواقع لعناوين IP."),
("Réseaux","Adressage","Difficile","Quel préfixe CIDR correspond au masque 255.255.255.0 ?","شنو CIDR ديال 255.255.255.0؟",["/8","/16","/24","/32"],["/8","/16","/24","/32"],2,"24 bits sont à 1 dans ce masque.","فهاد الماسك كاينين 24 bit قيمتهم 1."),
("Architecture","CPU","Facile","Quel composant exécute les instructions ?","شنو المكون اللي كينفذ التعليمات؟",["CPU","SSD","Écran","Clavier"],["CPU","SSD","الشاشة","لوحة المفاتيح"],0,"Le processeur exécute les instructions.","المعالج كينفذ التعليمات."),
("Architecture","Mémoire","Moyen","Quelle mémoire est généralement la plus rapide ?","شنو الذاكرة الأسرع غالبا؟",["Disque dur","RAM","Cache CPU","Clé USB"],["قرص صلب","RAM","Cache CPU","USB"],2,"Le cache CPU est plus rapide que la RAM.","Cache ديال CPU أسرع من RAM."),
("Architecture","Unité de calcul","Difficile","Quel est le rôle de l’ALU ?","شنو الدور ديال ALU؟",["Gérer les fichiers","Opérations arithmétiques et logiques","Rafraîchir l’écran","Connecter au réseau"],["تسيير الملفات","عمليات حسابية ومنطقية","تحديث الشاشة","الاتصال بالشبكة"],1,"L’ALU effectue les opérations arithmétiques et logiques.","ALU كتقوم بالعمليات الحسابية والمنطقية."),
("Bureautique","Excel","Facile","Quelle formule additionne A1 à A5 dans Excel français ?","شنو الفورمول اللي كتجمع A1 حتى A5 فـ Excel بالفرنسية؟",["=ADD(A1:A5)","=SOMME(A1:A5)","=TOTAL(A1:A5)","=PLUS(A1:A5)"],["=ADD(A1:A5)","=SOMME(A1:A5)","=TOTAL(A1:A5)","=PLUS(A1:A5)"],1,"La fonction française est SOMME.","فـ Excel بالفرنسية كنستعملو SOMME."),
("Bureautique","Excel","Moyen","Que signifie la référence absolue $A$1 ?","شنو كتعني référence absolue $A$1؟",["Elle change toujours","Elle reste fixe lors de la recopie","Elle supprime la cellule","Elle trie la colonne"],["كتتبدل ديما","كتبقى ثابتة ملي كننسخو الفورمول","كتحيد الخانة","كترتب العمود"],1,"Les signes $ figent la colonne et la ligne.","علامة $ كتثبت العمود والسطر."),
("Bureautique","Analyse","Difficile","Quel outil synthétise rapidement de grandes données ?","شنو الأداة اللي كتلخص كمية كبيرة ديال البيانات؟",["Publipostage","Tableau croisé dynamique","Correcteur","Thème"],["دمج المراسلات","جدول محوري","التصحيح","القالب"],1,"Le tableau croisé dynamique agrège les données.","Pivot table كتجمع وكتلخص البيانات."),
("Multimédia","Image","Facile","Quel format est adapté aux photographies compressées ?","شنو الفورما المناسبة للصور الفوتوغرافية المضغوطة؟",["JPEG","TXT","CSV","EXE"],["JPEG","TXT","CSV","EXE"],0,"JPEG est un format d’image avec compression avec perte.","JPEG صيغة صور فيها ضغط مع فقدان جزء من الجودة."),
("Multimédia","Image","Moyen","Que décrit la résolution d’une image ?","شنو كتوصف résolution ديال الصورة؟",["Nombre de pixels","Durée audio","Débit réseau","Fréquence CPU"],["عدد pixels","مدة الصوت","سرعة الشبكة","تردد CPU"],0,"La résolution décrit les dimensions en pixels.","الدقة كتحدد أبعاد الصورة بالـ pixels."),
("Multimédia","Audio","Difficile","Quels paramètres influencent le débit audio non compressé ?","شنو العوامل اللي كتأثر على débit ديال الصوت غير المضغوط؟",["Fréquence et profondeur","Couleur","Nom fichier","Taille écran"],["Sampling rate و bit depth","اللون","اسم الملف","حجم الشاشة"],0,"La fréquence d’échantillonnage et la profondeur en bits influencent le débit.","Sampling rate و bit depth كيأثرو على حجم الصوت.")
]
COURSE_SLUGS={name:slug for name,slug in zip([d[0] for d in DOMAINS],["algorithmique","programmation","bases-de-donnees","systemes","reseaux","architecture","bureautique","multimedia"])}

def configured_domains():
    """Official configured subjects plus administrator-created academy subjects."""
    rows=list(DOMAINS)
    if has_app_context():
        known={row[0] for row in rows}
        for subject in CurriculumSubject.query.order_by(CurriculumSubject.position,CurriculumSubject.name).all():
            if subject.name not in known: rows.append((subject.name,subject.weight,subject.category)); known.add(subject.name)
    return rows

def validate_email(form,field):
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",field.data or ""):
        raise ValidationError("Saisis une adresse email valide.")

def extract_youtube_video_id(raw_url):
    """Accept only canonical HTTPS YouTube watch, share, embed and Shorts URLs."""
    try:
        parsed=urlparse((raw_url or "").strip())
        host=(parsed.hostname or "").lower()
        port=parsed.port
    except ValueError:
        return None
    if parsed.scheme!="https" or parsed.username or parsed.password or port not in {None,443}:
        return None
    video_id=""
    if host in {"youtu.be","www.youtu.be"}:
        parts=parsed.path.strip("/").split("/")
        if len(parts)==1: video_id=parts[0]
    elif host in {"youtube.com","www.youtube.com","m.youtube.com"}:
        if parsed.path=="/watch": video_id=parse_qs(parsed.query).get("v",[""])[0]
        elif parsed.path.startswith(("/embed/","/shorts/")):
            parts=parsed.path.split("/")
            if len(parts)==3: video_id=parts[2]
    return video_id if re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id or "") else None

class RegisterForm(FlaskForm):
    username=StringField("Nom d’utilisateur",validators=[DataRequired(),Length(min=3,max=40)])
    email=StringField("Email",validators=[DataRequired(),Length(max=120),validate_email])
    password=PasswordField("Mot de passe",validators=[DataRequired(),Length(min=8)])
    confirm=PasswordField("Confirmer",validators=[DataRequired(),EqualTo("password")])
class LoginForm(FlaskForm):
    username=StringField("Nom d’utilisateur",validators=[DataRequired()])
    password=PasswordField("Mot de passe",validators=[DataRequired()])
class ProfileForm(FlaskForm):
    email=StringField("Adresse email",validators=[DataRequired(),Length(max=120),validate_email])
    current_password=PasswordField("Mot de passe actuel")
    new_password=PasswordField("Nouveau mot de passe",validators=[Length(max=128)])
class StudyForm(FlaskForm):
    domain=SelectField("Matière",choices=[(x[0],x[0]) for x in DOMAINS])
    minutes=IntegerField("Durée (minutes)",validators=[DataRequired(),NumberRange(min=1,max=720)])

def seed_curriculum():
    """Add original starter curriculum without overwriting administrator edits."""
    seeded={row.subject_slug for row in CurriculumSeedState.query.all()}
    for subject_index,item in enumerate(CURRICULUM):
        slug=COURSE_SLUGS[item["subject"]]
        if slug in seeded: continue
        subject=CurriculumSubject.query.filter_by(slug=slug).first()
        if not subject:
            domain=next(row for row in DOMAINS if row[0]==item["subject"])
            subject=CurriculumSubject(slug=slug,name=domain[0],category=domain[2],weight=domain[1],position=subject_index)
            db.session.add(subject); db.session.flush()
        for module_index,module_data in enumerate(item["modules"]):
            module=CurriculumModule(subject_id=subject.id,title=module_data["title"],position=module_index)
            db.session.add(module); db.session.flush()
            for chapter_index,chapter_data in enumerate(module_data["chapters"]):
                chapter=CurriculumChapter(module_id=module.id,title=chapter_data["title"],position=chapter_index)
                db.session.add(chapter); db.session.flush()
                lesson_data=chapter_data["lesson"]
                lesson=CurriculumLesson(chapter_id=chapter.id,title=lesson_data["title"],objectives_fr=json.dumps(lesson_data["objectives"],ensure_ascii=False),prerequisites_fr=lesson_data["prerequisites"],theory_fr=enrich_theory(chapter_data["title"],lesson_data["theory"]),theory_ar=lesson_data["darija"],example_fr=lesson_data["example"],code_example=lesson_data["code"],exercise_fr=lesson_data["exercise"],solution_fr=lesson_data["solution"],summary_fr=lesson_data["summary"],revision_fr=lesson_data["revision"])
                db.session.add(lesson); db.session.flush()
                db.session.add(CourseExercise(lesson_id=lesson.id,title="Exercice guidé",prompt_fr=lesson_data["exercise"],solution_fr=lesson_data["solution"],level="Moyen"))
        db.session.add(CurriculumSeedState(subject_slug=slug))
    db.session.commit()

def seed_questions():
    """Idempotently add the built-in bank while retaining existing question rows."""
    seed_curriculum()
    enrich_seeded_lessons()
    seed_phase6_exercises()
    seed_phase7_exercises()
    seed_phase8_lesson_material()
    chapters_by_domain={}
    for subject in CurriculumSubject.query.all():
        chapters=(CurriculumChapter.query.join(CurriculumModule).filter(CurriculumModule.subject_id==subject.id).order_by(CurriculumModule.position,CurriculumChapter.position).all())
        chapters_by_domain[subject.name]=chapters
    rows=[]
    rows.extend((row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9]) for row in SEED)
    rows.extend((domain,topic,level,prompt,"",options,options,answer,explanation,"") for domain,topic,level,prompt,options,answer,explanation in QUESTION_BANK)
    rows.extend((domain,topic,level,prompt,"",options,options,answer,explanation,"") for domain,topic,level,prompt,options,answer,explanation in PHASE6_QUESTIONS)
    existing={(question.domain,question.prompt_fr):question for question in Question.query.all()}
    metadata_ids={meta.question_id for meta in QuestionMetadata.query.all()}
    pending=[]
    for domain,topic,level,prompt,prompt_ar,options_fr,options_ar,answer,explanation_fr,explanation_ar in rows:
        question=existing.get((domain,prompt))
        if not question:
            question=Question(domain=domain,topic=topic,level=level,prompt_fr=prompt,prompt_ar=prompt_ar,options_fr=json.dumps(options_fr,ensure_ascii=False),options_ar=json.dumps(options_ar,ensure_ascii=False),answer=answer,explanation_fr=explanation_fr,explanation_ar=explanation_ar,active=True)
            db.session.add(question); pending.append((question,domain,topic)); existing[(domain,prompt)]=question
    if pending: db.session.flush()
    new_metadata=[]
    for question,domain,topic in pending:
        if question.id in metadata_ids: continue
        domain_chapters=chapters_by_domain.get(domain,[])
        chapter_title=SEED_TOPIC_CHAPTERS.get((domain,topic),topic)
        chapter=next((candidate for candidate in domain_chapters if candidate.title==chapter_title),domain_chapters[0] if domain_chapters else None)
        if chapter:
            lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first()
            objectives=json.loads(lesson.objectives_fr or "[]") if lesson else []
            new_metadata.append(QuestionMetadata(question_id=question.id,chapter_id=chapter.id,lesson_id=lesson.id if lesson else None,learning_objective=objectives[0] if objectives else chapter.title))
    missing_metadata=[q for q in existing.values() if q.id not in metadata_ids and q not in [p[0] for p in pending]]
    for question in missing_metadata:
        domain_chapters=chapters_by_domain.get(question.domain,[])
        chapter_title=SEED_TOPIC_CHAPTERS.get((question.domain,question.topic),question.topic)
        chapter=next((candidate for candidate in domain_chapters if candidate.title==chapter_title),domain_chapters[0] if domain_chapters else None)
        if chapter:
            lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first()
            objectives=json.loads(lesson.objectives_fr or "[]") if lesson else []
            new_metadata.append(QuestionMetadata(question_id=question.id,chapter_id=chapter.id,lesson_id=lesson.id if lesson else None,learning_objective=objectives[0] if objectives else chapter.title))
    for metadata in QuestionMetadata.query.filter((QuestionMetadata.learning_objective=="")|(QuestionMetadata.learning_objective.is_(None))).all():
        chapter=db.session.get(CurriculumChapter,metadata.chapter_id) if metadata.chapter_id else None
        lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first() if chapter else None
        objectives=json.loads(lesson.objectives_fr or "[]") if lesson else []
        metadata.learning_objective=objectives[0] if objectives else (chapter.title if chapter else "")
    for metadata in QuestionMetadata.query.filter(QuestionMetadata.lesson_id.is_(None),QuestionMetadata.chapter_id.isnot(None)).all():
        lesson=CurriculumLesson.query.filter_by(chapter_id=metadata.chapter_id).first()
        if lesson: metadata.lesson_id=lesson.id
    if new_metadata: db.session.add_all(new_metadata)
    db.session.commit()

def enrich_seeded_lessons():
    """Enrich only untouched starter theory; preserve any admin-edited lesson."""
    changed=False
    for subject_data in CURRICULUM:
        subject=CurriculumSubject.query.filter_by(name=subject_data["subject"]).first()
        if not subject: continue
        for module_data in subject_data["modules"]:
            module=CurriculumModule.query.filter_by(subject_id=subject.id,title=module_data["title"]).first()
            if not module: continue
            for chapter_data in module_data["chapters"]:
                chapter=CurriculumChapter.query.filter_by(module_id=module.id,title=chapter_data["title"]).first()
                lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first() if chapter else None
                if not lesson: continue
                original=chapter_data["lesson"]["theory"]
                enriched=enrich_theory(chapter_data["title"],original)
                if (lesson.theory_fr or "").strip()==original.strip():
                    lesson.theory_fr=enriched; changed=True
    if changed: db.session.commit()

def seed_phase6_exercises():
    """Add one distinct application problem per seeded chapter, without replacing edits."""
    added=False
    for chapter_title,(title,prompt,solution,level) in PHASE6_EXERCISES.items():
        chapter=CurriculumChapter.query.filter_by(title=chapter_title).first()
        if not chapter: continue
        lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first()
        if not lesson or CourseExercise.query.filter_by(lesson_id=lesson.id,title=title).first(): continue
        db.session.add(CourseExercise(lesson_id=lesson.id,title=title,prompt_fr=prompt,solution_fr=solution,grading_guide_fr="Évaluer la démarche, la justification et la cohérence du résultat.",level=level,published=True))
        added=True
    if added: db.session.commit()

def seed_phase7_exercises():
    """Add five lesson-linked, manually assessed practice tasks without editing existing work."""
    added=False
    lessons=CurriculumLesson.query.order_by(CurriculumLesson.id).all()
    for lesson in lessons:
        objectives=[]
        try: objectives=json.loads(lesson.objectives_fr or "[]")
        except (TypeError,ValueError): pass
        objective=(objectives[0] if objectives else lesson.title).strip()
        source_prompt=(lesson.exercise_fr or "").strip()
        source_solution=(lesson.solution_fr or "").strip()
        if len(source_prompt)<15: source_prompt=f"Explique et applique les notions centrales de « {lesson.title} »."
        if len(source_solution)<30: source_solution=f"Une réponse satisfaisante doit définir les notions de « {lesson.title} », exposer une démarche correcte et vérifier le résultat avec un exemple cohérent."
        tasks=[
            ("Débutant — repérer la notion",f"À partir de la situation de la leçon (« {source_prompt[:500]} »), nomme la notion principale et reformule-la avec tes propres mots. Donne un indice du problème qui te permet de la reconnaître.","La correction attend l’identification de la notion travaillée, une reformulation exacte et un indice cité dans l’énoncé. Comparer avec le corrigé guidé : "+source_solution[:1800]),
            ("Élémentaire — expliquer la démarche",f"Pour l’objectif « {objective} », décris les étapes à suivre dans l’ordre. À chaque étape, précise l’information utilisée et le résultat attendu.","La correction doit suivre une démarche ordonnée et relier chaque action à son résultat. Réponse de référence de la leçon : "+source_solution[:1800]),
            ("Intermédiaire — transférer",f"Construis un nouvel exemple (différent de celui de la leçon) qui mobilise « {objective} ». Résous-le et justifie chaque décision; indique une vérification indépendante du résultat.","Il n’existe pas un unique exemple attendu. La réponse doit être nouvelle, pertinente pour l’objectif, correctement résolue et accompagnée d’une vérification. Repères : "+source_solution[:1600]),
            ("Avancé — diagnostiquer une erreur",f"Un apprenant traite mal une situation liée à « {objective} ». Invente une erreur plausible, montre l’étape fautive, explique sa conséquence et propose une correction vérifiable.","La correction évalue quatre éléments : erreur techniquement plausible, localisation précise, explication de la conséquence et démarche corrigée. Les repères de résolution sont : "+source_solution[:1600]),
            ("Défi concours — synthèse argumentée",f"Résous la situation suivante en mobilisant « {objective} » : {source_prompt[:700]} Présente les hypothèses, la démarche, le résultat et une justification qui permet à un correcteur de suivre ton raisonnement.","Barème indicatif : hypothèses pertinentes, méthode cohérente, résultat correct, justification lisible et contrôle final. Pour la situation de base, les éléments de correction sont : "+source_solution[:1600]),
        ]
        for title,prompt,solution in tasks:
            if CourseExercise.query.filter_by(lesson_id=lesson.id,title=title).first(): continue
            db.session.add(CourseExercise(lesson_id=lesson.id,title=title,prompt_fr=prompt,solution_fr=solution,
                exercise_type="open",grading_guide_fr="Réponse libre : aucune note automatique. L’enseignant évalue la justesse, la démarche et la justification.",
                level=title.split(" — ",1)[0],learning_objective_fr=objective,published=True))
            added=True
    if added: db.session.commit()

def seed_phase8_lesson_material():
    """Add chapter-specific instruction only to untouched built-in lessons."""
    changed=False
    for subject_data in CURRICULUM:
        subject=CurriculumSubject.query.filter_by(name=subject_data["subject"]).first()
        if not subject: continue
        for module_data in subject_data["modules"]:
            module=CurriculumModule.query.filter_by(subject_id=subject.id,title=module_data["title"]).first()
            if not module: continue
            for chapter_data in module_data["chapters"]:
                chapter=CurriculumChapter.query.filter_by(module_id=module.id,title=chapter_data["title"]).first()
                lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first() if chapter else None
                detail=PHASE8_DETAILS.get(chapter_data["title"])
                if not lesson or not detail: continue
                original=chapter_data["lesson"]
                baseline_theory=enrich_theory(chapter_data["title"],original["theory"])
                marker="EXEMPLES PRATIQUES DISTINCTS — ÉTUDE GUIDÉE"
                if (lesson.theory_fr or "").strip()==baseline_theory.strip():
                    blocks=[baseline_theory.strip(),"\n\nPOURQUOI CE SUJET EST UTILE\n"+WHY_IT_MATTERS[chapter_data["title"]],"\n\nVOCABULAIRE ET DÉFINITIONS\n"+"\n".join(f"• {item}" for item in detail["terms"]),"\n\nNOTIONS EXPLIQUÉES\n"+"\n\n".join(detail["sections"]),"\n\nDÉMONSTRATION PAS À PAS\n"+detail["demo"],"\n\n"+marker+"\n"+"\n".join(f"\nExemple {i}: {item}" for i,item in enumerate(detail["examples"],1)),"\n\n5 POINTS ESSENTIELS À RETENIR\n"+"\n".join(f"• {item}" for item in detail["review"])]
                    lesson.theory_fr="".join(blocks); changed=True
                try: current_objectives=json.loads(lesson.objectives_fr or "[]")
                except (TypeError,ValueError): current_objectives=[]
                if current_objectives==original["objectives"]:
                    lesson.objectives_fr=json.dumps(original["objectives"]+detail["objectives"],ensure_ascii=False); changed=True
                if (lesson.example_fr or "").strip()==original["example"].strip():
                    lesson.example_fr="\n\n".join(f"Exemple {i}: {item}" for i,item in enumerate(detail["examples"],1)); changed=True
                code=CODE_EXAMPLES.get(chapter_data["title"])
                if code and (lesson.code_example or "").strip()==original["code"].strip():
                    lesson.code_example=code; changed=True
    if changed: db.session.commit()

def calculate_mastery(user_id,since=None):
    """Return activity-backed mastery; small samples stay visibly low-confidence."""
    domains=configured_domains()
    observations={name:[] for name,_,_ in domains}
    topic_observations={name:{} for name,_,_ in domains}
    diagnostic_query=Diagnostic.query.filter_by(user_id=user_id)
    if since: diagnostic_query=diagnostic_query.filter(Diagnostic.created_at>=since)
    diagnostics=diagnostic_query.order_by(Diagnostic.created_at.asc()).all()
    for d in diagnostics:
        for name,entry in json.loads(d.scores).items():
            if name in observations and entry.get("count",0)>0:
                observations[name].append((d.created_at,float(entry["percent"]),int(entry["count"]),"Diagnostic"))
    attempt_query=Attempt.query.filter_by(user_id=user_id).filter(Attempt.mode.in_(["qcm","exam"]))
    if since: attempt_query=attempt_query.filter(Attempt.created_at>=since)
    attempts=attempt_query.order_by(Attempt.created_at.asc()).all()
    for a in attempts:
        by_domain={}
        for item in json.loads(a.details or "[]"):
            name=item.get("domain")
            if name in observations:
                row=by_domain.setdefault(name,[0,0]); row[1]+=1; row[0]+=int(bool(item.get("ok")))
                topic=item.get("topic")
                if topic:
                    topic_observations[name].setdefault(topic,[]).append((a.created_at,int(bool(item.get("ok")))))
        for name,(correct,count) in by_domain.items():
            observations[name].append((a.created_at,correct*100/count,count,"Exercice" if a.mode=="qcm" else "Examen blanc"))
    exercise_query=ExerciseAttempt.query.filter(ExerciseAttempt.status.in_(["auto_graded","ai_graded"])).filter(ExerciseAttempt.score.isnot(None))
    if since: exercise_query=exercise_query.filter(ExerciseAttempt.created_at>=since)
    for evaluated in exercise_query.order_by(ExerciseAttempt.created_at.asc()).all():
        exercise=db.session.get(CourseExercise,evaluated.exercise_id)
        lesson=db.session.get(CurriculumLesson,exercise.lesson_id) if exercise else None
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id) if lesson else None
        module=db.session.get(CurriculumModule,chapter.module_id) if chapter else None
        subject=db.session.get(CurriculumSubject,module.subject_id) if module else None
        if subject and subject.name in observations:
            score=float(evaluated.score)
            observations[subject.name].append((evaluated.created_at,score,1,"Exercice évalué automatiquement"))
            topic_observations[subject.name].setdefault(chapter.title,[]).append((evaluated.created_at,score/100))
    result={}
    now=utcnow()
    for name,weight,_ in domains:
        rows=observations[name]
        topic_scores=[]
        for topic,topic_rows in topic_observations[name].items():
            denominator=0; numerator=0
            for when,ok in topic_rows:
                recency=0.55**(max(0,(now-when).days)/60)
                denominator+=recency; numerator+=recency*ok
            if denominator and len(topic_rows)>=3: topic_scores.append({"name":topic,"percent":round(100*numerator/denominator),"count":len(topic_rows)})
        topic_scores.sort(key=lambda x:x["percent"],reverse=True)
        if not rows:
            result[name]={"percent":None,"confidence":"Insuffisante","count":0,"correct":0,"previous":None,"last":None,"weight":weight,"level":None,"topics":topic_scores}; continue
        evidence_count=sum(row[2] for row in rows)
        if evidence_count<3:
            result[name]={"percent":None,"confidence":"Insuffisante","count":evidence_count,"correct":sum(round(row[1]*row[2]/100) for row in rows),"previous":None,"last":max(row[0] for row in rows).strftime("%d/%m/%Y"),"weight":weight,"level":None,"topics":topic_scores}; continue
        weighted=[]; total_evidence=0
        for when,score,n,source in rows:
            age=max(0,(now-when).days)
            recency=0.55**(age/60)
            sample=min(1,n/5)
            weighted.append((score,recency*sample,n,when,source))
            total_evidence+=n
        denom=sum(x[1] for x in weighted)
        score=round(sum(x[0]*x[1] for x in weighted)/denom) if denom else None
        previous_rows=weighted[:-1]
        previous=round(sum(x[0]*x[1] for x in previous_rows)/sum(x[1] for x in previous_rows)) if previous_rows and sum(x[1] for x in previous_rows) else None
        confidence="Élevée" if total_evidence>=20 else "Moyenne" if total_evidence>=8 else "Faible"
        level="Débutant" if score<40 else "En progression" if score<60 else "Bon niveau" if score<80 else "Très bon niveau" if score<95 else "Maîtrise excellente"
        result[name]={"percent":score,"confidence":confidence,"count":total_evidence,"correct":sum(round(x[0]*x[2]/100) for x in weighted),"previous":previous,"last":max(x[3] for x in weighted).strftime("%d/%m/%Y"),"weight":weight,"level":level,"topics":topic_scores}
    return result

def build_study_recommendations(user_id):
    """Build a small, explainable plan from this user's stored assessment evidence."""
    mastery=calculate_mastery(user_id)
    observed=[(name,score) for name,score in mastery.items() if score["percent"] is not None]
    observed.sort(key=lambda pair:(pair[1]["percent"], -pair[1]["weight"]))
    if not observed:
        return [], False
    recommendations=[]
    for rank,(domain,score) in enumerate(observed[:3],start=1):
        weak_topics=sorted(score["topics"],key=lambda topic:(topic["percent"],-topic["count"]))
        topic=weak_topics[0] if weak_topics else None
        subject=CurriculumSubject.query.filter_by(name=domain).first()
        slug=subject.slug if subject else COURSE_SLUGS.get(domain)
        if not slug: continue
        chapter=CurriculumChapter.query.filter_by(title=topic["name"]).join(CurriculumModule).join(CurriculumSubject).filter(CurriculumSubject.slug==slug).first() if topic else None
        if not chapter: chapter=CurriculumChapter.query.join(CurriculumModule).join(CurriculumSubject).filter(CurriculumSubject.slug==slug,CurriculumChapter.published.is_(True),CurriculumModule.published.is_(True)).order_by(CurriculumModule.position,CurriculumChapter.position).first()
        lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id,published=True).first() if chapter else None
        progress=LessonProgress.query.filter_by(user_id=user_id,lesson_key=f"lesson:{lesson.id}").first() if lesson else None
        stage=adaptive_level_for_score(score["percent"],current_app.config.get("ADAPTIVE_THRESHOLDS",[40,60,75,90]))
        if score["percent"]<40: why="Les réponses évaluées montrent qu’un retour aux bases serait utile."
        elif score["percent"]<60: why="Consolide les notions avant de passer aux exercices plus complexes."
        elif score["percent"]<75: why="Les résultats suggèrent de poursuivre avec des exercices intermédiaires."
        elif score["percent"]<90: why="Travaille des applications avancées pour entretenir ce niveau."
        else: why="Les résultats sont solides; vise des exercices de synthèse et de défi."
        recommendations.append({"day":rank,"subject":domain,"topic":topic["name"] if topic else None,
            "topic_percent":topic["percent"] if topic else None,"priority":"Élevée" if score["percent"]<60 else "À consolider" if score["percent"]<80 else "Entretien",
            "minutes":45,"slug":slug,"lesson_id":lesson.id if lesson else None,"exercise_url":f"/qcm?domain={domain}&adaptive=1",
            "status":"Palier validé" if progress else "À faire","percent":score["percent"],"count":score["count"],"level":stage,"why":why})
    return recommendations, True

ADAPTIVE_STAGES=("Débutant","Élémentaire","Intermédiaire","Avancé","Expert / défi")
ADAPTIVE_QUESTION_LEVELS={
    "Débutant":{"Facile","Débutant"},
    "Élémentaire":{"Facile","Moyen","Débutant","Élémentaire"},
    "Intermédiaire":{"Moyen","Intermédiaire"},
    "Avancé":{"Moyen","Difficile","Avancé"},
    "Expert / défi":{"Difficile","Avancé","Expert"},
}
QUESTION_LEVELS=("Débutant","Élémentaire","Intermédiaire","Avancé","Expert","Facile","Moyen","Difficile")

def adaptive_level_for_score(score,thresholds=None):
    """Map an evaluated score to a configurable practice band."""
    cuts=thresholds or [40,60,75,90]
    try: value=max(0,min(100,float(score)))
    except (TypeError,ValueError): return None
    return ADAPTIVE_STAGES[sum(value>=cut for cut in cuts)]

def adaptive_question_set(user_id,domain=None,topic=None,limit=15,thresholds=None):
    """Select real questions by subject evidence, avoiding repeats when possible."""
    domains=[domain] if domain in {row[0] for row in DOMAINS} else [row[0] for row in DOMAINS]
    mastery=calculate_mastery(user_id)
    attempts=Attempt.query.filter_by(user_id=user_id).filter(Attempt.mode.in_(["qcm","exam"])).order_by(Attempt.created_at.desc()).limit(150).all()
    history={name:{} for name in domains}
    difficulty_observations={name:[] for name in domains}
    for attempt in attempts:
        for item in json.loads(attempt.details or "[]"):
            name=item.get("domain")
            if name not in history: continue
            qid=item.get("question_id")
            if qid is None: continue
            row=history[name].setdefault(int(qid),{"seen":0,"wrong":0})
            row["seen"]+=1
            row["wrong"]+=int(not bool(item.get("ok")))
            question=db.session.get(Question,int(qid))
            level=item.get("level") or (question.level if question else "Moyen")
            level_weight={"Facile":0.85,"Débutant":0.80,"Élémentaire":0.9,"Moyen":1.0,"Intermédiaire":1.0,"Avancé":1.1,"Difficile":1.15,"Expert":1.2}.get(level,1.0)
            recency=0.55**(max(0,(utcnow()-attempt.created_at).days)/60)
            difficulty_observations[name].append((int(bool(item.get("ok"))),level_weight*recency))
    rows=[row for row in DOMAINS if row[0] in domains]
    if domain in domains:
        quotas={domain:max(1,limit)}
    else:
        quotas={name:1 for name in domains[:min(limit,len(domains))]}
        remaining=max(0,limit-sum(quotas.values()))
        weights={name:weight*(1.35 if mastery[name]["percent"] is not None and mastery[name]["percent"]<60 else 1.0) for name,weight,_ in rows}
        total_weight=sum(weights.values()) or 1
        exact={name:remaining*weight/total_weight for name,weight in weights.items()}
        for name in exact: quotas[name]=quotas.get(name,0)+int(exact[name])
        for name in sorted(exact,key=lambda key:exact[key]-int(exact[key]),reverse=True)[:remaining-sum(int(v) for v in exact.values())]: quotas[name]+=1
    chosen=[]
    explanations=[]
    selected_allowed={}
    for name in domains:
        score=mastery[name]
        difficulty_rows=difficulty_observations.get(name,[])
        difficulty_percent=100*sum(ok*weight for ok,weight in difficulty_rows)/sum(weight for _,weight in difficulty_rows) if difficulty_rows else None
        stage_score=0.7*score["percent"]+0.3*difficulty_percent if score["percent"] is not None and len(difficulty_rows)>=3 else score["percent"]
        stage=adaptive_level_for_score(stage_score,thresholds) if stage_score is not None else None
        allowed=ADAPTIVE_QUESTION_LEVELS.get(stage, {"Facile","Moyen","Débutant","Élémentaire","Intermédiaire"})
        selected_allowed[name]=allowed
        base=Question.query.filter_by(domain=name,active=True)
        if topic: base=base.filter_by(topic=topic)
        pool=base.order_by(Question.id).all()
        matched=[q for q in pool if q.level in allowed]
        # A short, level-matched practice set is more useful than padding it
        # with questions outside the learner's estimated band.
        if not matched and stage is None: matched=pool
        hist=history.get(name,{})
        random.shuffle(matched)
        matched.sort(key=lambda q:(hist.get(q.id,{}).get("seen",0)>0,-hist.get(q.id,{}).get("wrong",0),hist.get(q.id,{}).get("seen",0)))
        take=quotas.get(name,0)
        selected=matched[:take]
        chosen.extend(selected)
        if selected:
            if stage is None: explanation=f"{name} : calibration initiale, avec des questions de base et intermédiaires; les résultats suffiront ensuite à ajuster le niveau."
            else: explanation=f"{name} : niveau {stage.lower()} estimé sur {score['count']} réponses évaluées; les erreurs récentes et les questions déjà vues sont prises en compte."
            explanations.append(explanation)
    if len(chosen)<limit and not any("niveau" in explanation for explanation in explanations):
        used={q.id for q in chosen}
        extra=Question.query.filter(Question.active.is_(True),Question.domain.in_(domains)).order_by(Question.id).all()
        random.shuffle(extra)
        chosen.extend(q for q in extra if q.id not in used and q.level in selected_allowed.get(q.domain,set()) and (not topic or q.topic==topic))
    random.shuffle(chosen)
    chosen=chosen[:max(0,limit)]
    return chosen, " ".join(explanations)

def register_routes(app):
    def auth_throttle_key(scope, identity=""):
        raw=f"{scope}|{request.remote_addr or 'unknown'}|{identity}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def is_throttled(key):
        row=db.session.get(AuthThrottle,key)
        if not row: return False
        if utcnow()-row.window_started>timedelta(minutes=15):
            db.session.delete(row); db.session.commit(); return False
        return row.attempts>=10

    def count_auth_failure(key):
        row=db.session.get(AuthThrottle,key)
        if not row or utcnow()-row.window_started>timedelta(minutes=15):
            if row: db.session.delete(row)
            row=AuthThrottle(key=key,window_started=utcnow(),attempts=0); db.session.add(row)
        row.attempts+=1; db.session.commit()

    @app.route("/")
    def home():
        if current_user.is_authenticated:return redirect(url_for("dashboard"))
        return render_template("landing.html",domains=DOMAINS)

    @app.route("/register",methods=["GET","POST"])
    def register():
        form=RegisterForm()
        throttle_key=auth_throttle_key("register")
        if request.method=="POST" and is_throttled(throttle_key): abort(429)
        if form.validate_on_submit():
            if User.query.filter((User.username==form.username.data.strip())|(User.email==form.email.data.strip().lower())).first():
                flash("Nom d’utilisateur ou email déjà utilisé.","error")
                count_auth_failure(throttle_key)
            else:
                u=User(username=form.username.data.strip(),email=form.email.data.strip().lower())
                u.set_password(form.password.data); db.session.add(u); db.session.commit()
                login_user(u); session["language"]="fr"; flash("Bienvenue sur InfoConcours !","success")
                return redirect(url_for("dashboard"))
        elif request.method=="POST": count_auth_failure(throttle_key)
        return render_template("auth.html",form=form,mode="register")

    @app.route("/login",methods=["GET","POST"])
    def login():
        form=LoginForm()
        throttle_key=auth_throttle_key("login",(request.form.get("username") or "").strip().lower())
        ip_throttle_key=auth_throttle_key("login-ip")
        if request.method=="POST" and (is_throttled(throttle_key) or is_throttled(ip_throttle_key)): abort(429)
        if form.validate_on_submit():
            u=User.query.filter_by(username=form.username.data.strip()).first()
            if u and u.check_password(form.password.data):
                login_user(u)
                preference=UserPreference.query.filter_by(user_id=u.id).first(); session["language"]=preference.language if preference else "fr"
                blocked=db.session.get(AuthThrottle,throttle_key)
                if blocked: db.session.delete(blocked); db.session.commit()
                blocked_ip=db.session.get(AuthThrottle,ip_throttle_key)
                if blocked_ip: db.session.delete(blocked_ip); db.session.commit()
                return redirect(url_for("dashboard"))
            flash("Identifiants incorrects.","error")
            count_auth_failure(throttle_key)
            count_auth_failure(ip_throttle_key)
        return render_template("auth.html",form=form,mode="login")

    @app.route("/logout",methods=["POST"])
    @login_required
    def logout(): logout_user(); return redirect(url_for("home"))

    @app.route("/profile",methods=["GET","POST"])
    @login_required
    def profile():
        form=ProfileForm()
        if request.method=="GET": form.email.data=current_user.email
        if request.method=="POST" and form.validate_on_submit():
            action=request.form.get("action")
            if action=="email":
                new_email=form.email.data.strip().lower()
                other=User.query.filter(User.email==new_email,User.id!=current_user.id).first()
                if other: flash("Cette adresse est déjà utilisée.","error")
                else:
                    current_user.email=new_email; db.session.commit(); flash("Adresse mise à jour.","success")
            elif action=="password":
                confirm=request.form.get("confirm_password","")
                if not current_user.check_password(form.current_password.data or ""):
                    flash("Le mot de passe actuel est incorrect.","error")
                elif len(form.new_password.data or "")<8 or form.new_password.data!=confirm:
                    flash("Le nouveau mot de passe doit contenir au moins 8 caractères et correspondre à la confirmation.","error")
                else:
                    current_user.set_password(form.new_password.data); db.session.commit(); flash("Mot de passe mis à jour.","success")
            else: abort(400)
            return redirect(url_for("profile"))
        return render_template("profile.html",form=form)

    @app.route("/dashboard")
    @login_required
    def dashboard():
        period=request.args.get("period","all")
        if period not in {"week","month","all"}: period="all"
        since=utcnow()-timedelta(days=7 if period=="week" else 30) if period!="all" else None
        latest=Diagnostic.query.filter_by(user_id=current_user.id).order_by(Diagnostic.created_at.desc()).first()
        today_minutes=db.session.query(db.func.coalesce(db.func.sum(StudySession.minutes),0)).filter_by(user_id=current_user.id,studied_on=date.today()).scalar()
        goal=StudyGoal.query.filter_by(user_id=current_user.id).first()
        activity_rows=db.session.query(StudySession.studied_on,db.func.sum(StudySession.minutes)).filter(StudySession.user_id==current_user.id,StudySession.studied_on>=date.today()-timedelta(days=29)).group_by(StudySession.studied_on).order_by(StudySession.studied_on.asc()).all()
        activity={d.isoformat():int(m) for d,m in activity_rows}
        study_trend=[{"date":(date.today()-timedelta(days=offset)).strftime("%d/%m"),"minutes":activity.get((date.today()-timedelta(days=offset)).isoformat(),0)} for offset in range(29,-1,-1)]
        studied_days={row[0] for row in db.session.query(StudySession.studied_on).filter_by(user_id=current_user.id).distinct().all()}
        streak=0; check=date.today()
        if check not in studied_days: check-=timedelta(days=1)
        while check in studied_days: streak+=1; check-=timedelta(days=1)
        attempt_query=Attempt.query.filter_by(user_id=current_user.id)
        if since: attempt_query=attempt_query.filter(Attempt.created_at>=since)
        attempts=attempt_query.order_by(Attempt.created_at.desc()).limit(8).all()
        trend_rows=list(reversed(attempt_query.order_by(Attempt.created_at.desc()).limit(100).all()))
        trend=[{"date":a.created_at.strftime("%d/%m"),"percent":round(a.score*100/a.total) if a.total else 0} for a in trend_rows]
        qcm_query=Attempt.query.filter_by(user_id=current_user.id,mode="qcm")
        if since: qcm_query=qcm_query.filter(Attempt.created_at>=since)
        total_q=qcm_query.count()
        avg=db.session.query(db.func.avg(Attempt.score*100.0/Attempt.total)).filter(Attempt.user_id==current_user.id,Attempt.mode=="qcm",Attempt.created_at>=since if since else True).scalar() or 0
        mastery=calculate_mastery(current_user.id,since)
        recommendations,personalized=build_study_recommendations(current_user.id)
        published_lessons=CurriculumLesson.query.join(CurriculumChapter).join(CurriculumModule).join(CurriculumSubject).filter(CurriculumLesson.published.is_(True),CurriculumChapter.published.is_(True),CurriculumModule.published.is_(True),CurriculumSubject.published.is_(True)).count()
        completed_lessons=LessonCompletion.query.filter_by(user_id=current_user.id).join(CurriculumLesson).filter(CurriculumLesson.published.is_(True)).count()
        return render_template("dashboard.html",latest=latest,scores=mastery,today_minutes=today_minutes,attempts=attempts,total_q=total_q,avg=round(avg),trend=trend,study_goal=goal.daily_minutes if goal else None,goal_percent=min(100,round(today_minutes*100/goal.daily_minutes)) if goal else None,streak=streak,study_trend=study_trend,period=period,recommendations=recommendations,personalized=personalized,published_lessons=published_lessons,completed_lessons=completed_lessons)

    @app.route("/diagnostic",methods=["GET","POST"])
    @login_required
    def diagnostic():
        if request.method=="POST":
            issued=session.pop("active_diagnostic_ids",None)
            qs=Question.query.filter(Question.active.is_(True),Question.id.in_(issued)).all() if issued else Question.query.filter_by(active=True).all()
        else:
            qs=[]
            for name,_,_ in configured_domains():
                sample,_=adaptive_question_set(current_user.id,domain=name,limit=3,thresholds=current_app.config["ADAPTIVE_THRESHOLDS"])
                qs.extend(sample)
            session["active_diagnostic_ids"]=[q.id for q in qs]
        if request.method=="POST":
            scores={}; total=0
            for domain,weight,group in configured_domains():
                group_q=[q for q in qs if q.domain==domain]
                answered=[q for q in group_q if request.form.get("q"+str(q.id)) in {str(i) for i in range(4)}]
                correct=sum(1 for q in answered if request.form.get("q"+str(q.id))==str(q.answer))
                total+=correct
                scores[domain]={"correct":correct,"count":len(answered),"available":len(group_q),"percent":round(correct/len(answered)*100) if answered else 0,"weight":weight}
            result=Diagnostic(user_id=current_user.id,scores=json.dumps(scores,ensure_ascii=False),total=total)
            db.session.add(result); db.session.commit()
            return redirect(url_for("diagnostic_result",id=result.id))
        time_limits={row.question_id:row.time_limit_seconds for row in QuestionMetadata.query.filter(QuestionMetadata.time_limit_seconds.isnot(None)).all()}
        learning_objectives={row.question_id:row.learning_objective for row in QuestionMetadata.query.all()}
        return render_template("diagnostic.html",questions=qs,time_limits=time_limits,learning_objectives=learning_objectives)

    @app.route("/diagnostic/<int:id>")
    @login_required
    def diagnostic_result(id):
        d=Diagnostic.query.filter_by(id=id,user_id=current_user.id).first_or_404()
        scores=json.loads(d.scores); evaluated=[(name,entry) for name,entry in scores.items() if entry.get("count",0)>0]
        weak=sorted(evaluated,key=lambda x:x[1]["percent"])
        denominator=sum(entry["weight"] for _,entry in evaluated)
        overall=round(sum(entry["percent"]*entry["weight"] for _,entry in evaluated)/denominator) if denominator else None
        return render_template("diagnostic_result.html",diagnostic=d,scores=scores,weak=weak,evaluated=evaluated,overall=overall)

    @app.route("/courses")
    @login_required
    def courses():
        subjects=CurriculumSubject.query.filter_by(published=True).order_by(CurriculumSubject.position).all()
        rows=[]
        completed_ids={row.lesson_id for row in LessonCompletion.query.filter_by(user_id=current_user.id).all()}
        for subject in subjects:
            modules=CurriculumModule.query.filter_by(subject_id=subject.id,published=True).order_by(CurriculumModule.position).all()
            module_rows=[]
            for module in modules:
                chapters=CurriculumChapter.query.filter_by(module_id=module.id,published=True).order_by(CurriculumChapter.position).all()
                chapter_rows=[]
                for chapter in chapters:
                    lessons=CurriculumLesson.query.filter_by(chapter_id=chapter.id,published=True).order_by(CurriculumLesson.id).all()
                    if lessons: chapter_rows.append({"chapter":chapter,"lessons":lessons})
                if chapter_rows: module_rows.append({"module":module,"chapters":chapter_rows})
            lessons=[lesson for mr in module_rows for cr in mr["chapters"] for lesson in cr["lessons"]]
            completed_count=sum(lesson.id in completed_ids for lesson in lessons)
            if module_rows: rows.append({"subject":subject,"modules":module_rows,"lesson_count":len(lessons),"completed_count":completed_count,"progress_percent":round(completed_count*100/len(lessons)) if lessons else 0})
        visited_ids=set()
        for row in LessonProgress.query.filter_by(user_id=current_user.id).filter(LessonProgress.lesson_key.like("lesson:%")).all():
            try: visited_ids.add(int(row.lesson_key.split(":",1)[1]))
            except (ValueError,IndexError): pass
        candidate=None
        visits=LessonProgress.query.filter_by(user_id=current_user.id).filter(LessonProgress.lesson_key.like("lesson:%")).order_by(LessonProgress.updated_at.desc()).all()
        for visit in visits:
            try: candidate=CurriculumLesson.query.filter_by(id=int(visit.lesson_key.split(":",1)[1]),published=True).first()
            except (ValueError,IndexError): candidate=None
            if candidate and candidate.id not in completed_ids: break
            candidate=None
        if not candidate:
            candidate=CurriculumLesson.query.join(CurriculumChapter).join(CurriculumModule).join(CurriculumSubject).filter(CurriculumLesson.published.is_(True),CurriculumChapter.published.is_(True),CurriculumModule.published.is_(True),CurriculumSubject.published.is_(True)).order_by(CurriculumSubject.position,CurriculumModule.position,CurriculumChapter.position,CurriculumLesson.id).all()
            candidate=next((lesson for lesson in candidate if lesson.id not in completed_ids),None)
        return render_template("courses.html",subjects=rows,completed_ids=completed_ids,visited_ids=visited_ids,continue_lesson=candidate)

    @app.route("/courses/continue")
    @login_required
    def continue_course():
        completed_ids={row.lesson_id for row in LessonCompletion.query.filter_by(user_id=current_user.id).all()}
        visits=LessonProgress.query.filter_by(user_id=current_user.id).filter(LessonProgress.lesson_key.like("lesson:%")).order_by(LessonProgress.updated_at.desc()).all()
        for visit in visits:
            try: lesson_id=int(visit.lesson_key.split(":",1)[1])
            except (ValueError,IndexError): continue
            lesson=CurriculumLesson.query.filter_by(id=lesson_id,published=True).join(CurriculumChapter).join(CurriculumModule).join(CurriculumSubject).filter(CurriculumChapter.published.is_(True),CurriculumModule.published.is_(True),CurriculumSubject.published.is_(True)).first()
            if lesson and lesson.id not in completed_ids:
                subject=db.session.get(CurriculumSubject,db.session.get(CurriculumModule,db.session.get(CurriculumChapter,lesson.chapter_id).module_id).subject_id)
                return redirect(url_for("lesson",slug=subject.slug,lesson_id=lesson.id))
        lessons=CurriculumLesson.query.join(CurriculumChapter).join(CurriculumModule).join(CurriculumSubject).filter(CurriculumLesson.published.is_(True),CurriculumChapter.published.is_(True),CurriculumModule.published.is_(True),CurriculumSubject.published.is_(True)).order_by(CurriculumSubject.position,CurriculumModule.position,CurriculumChapter.position,CurriculumLesson.id).all()
        lesson=next((item for item in lessons if item.id not in completed_ids),None)
        if not lesson: flash("Toutes les leçons publiées sont terminées.","success"); return redirect(url_for("courses"))
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id); module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        return redirect(url_for("lesson",slug=subject.slug,lesson_id=lesson.id))

    @app.route("/courses/<slug>",defaults={"lesson_id":None},methods=["GET","POST"])
    @app.route("/courses/<slug>/lesson/<int:lesson_id>",methods=["GET","POST"])
    @login_required
    def lesson(slug,lesson_id):
        subject=CurriculumSubject.query.filter_by(slug=slug,published=True).first_or_404()
        domain=subject.name
        if lesson_id is None:
            # Keep the legacy subject-level assessment endpoint for existing links.
            if request.method=="POST":
                questions=Question.query.filter_by(domain=domain,active=True).all(); details=[]; correct=0
                for q in questions:
                    answer=request.form.get("a"+str(q.id)); valid=answer is not None and answer.isdigit() and 0<=int(answer)<len(json.loads(q.options_fr)); ok=valid and answer==str(q.answer); correct+=int(ok)
                details.append({"question_id":q.id,"topic":q.topic,"domain":domain,"level":q.level,"prompt":q.prompt_fr,"prompt_ar":q.prompt_ar,"ok":ok,"explanation":q.explanation_fr,"explanation_ar":q.explanation_ar,"answer":q.answer,"options":json.loads(q.options_fr),"options_ar":json.loads(q.options_ar or "[]"),"selected":int(answer) if valid else None})
                if not details: flash("Aucun exercice actif n’est disponible pour cette matière.","error"); return redirect(url_for("lesson",slug=slug))
                db.session.add(Attempt(user_id=current_user.id,mode="qcm",score=correct,total=len(details),details=json.dumps(details,ensure_ascii=False)))
                progress=LessonProgress.query.filter_by(user_id=current_user.id,lesson_key=slug).first()
                if len(details)>=3 and correct/len(details)>=0.7:
                    progress=progress or LessonProgress(user_id=current_user.id,lesson_key=slug,evidence_count=0); progress.evidence_count+=len(details); db.session.add(progress)
                    flash("Palier validé sur l’évaluation de la matière.","success")
                db.session.commit(); return redirect(url_for("lesson",slug=slug))
            modules=CurriculumModule.query.filter_by(subject_id=subject.id,published=True).order_by(CurriculumModule.position).all()
            module_rows=[]
            for module in modules:
                chapters=CurriculumChapter.query.filter_by(module_id=module.id,published=True).order_by(CurriculumChapter.position).all()
                chapter_rows=[]
                for chapter in chapters:
                    lessons=CurriculumLesson.query.filter_by(chapter_id=chapter.id,published=True).order_by(CurriculumLesson.id).all()
                    if lessons: chapter_rows.append({"chapter":chapter,"lessons":lessons})
                if chapter_rows: module_rows.append({"module":module,"chapters":chapter_rows})
            completed_ids={row.lesson_id for row in LessonCompletion.query.filter_by(user_id=current_user.id).all()}
            visited_ids=set()
            for row in LessonProgress.query.filter_by(user_id=current_user.id).filter(LessonProgress.lesson_key.like("lesson:%")).all():
                try: visited_ids.add(int(row.lesson_key.split(":",1)[1]))
                except (ValueError,IndexError): pass
            return render_template("course_subject.html",subject=subject,modules=module_rows,completed_ids=completed_ids,visited_ids=visited_ids)
        lesson=CurriculumLesson.query.filter_by(id=lesson_id,published=True).first_or_404()
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id)
        module=db.session.get(CurriculumModule,chapter.module_id) if chapter else None
        if not chapter or not module or module.subject_id!=subject.id or not module.published or not chapter.published: abort(404)
        meta=QuestionMetadata.query.filter_by(chapter_id=chapter.id).all()
        qids=[row.question_id for row in meta]
        questions=Question.query.filter(Question.id.in_(qids),Question.active.is_(True)).order_by(Question.id).all() if qids else []
        lesson_key=f"lesson:{lesson.id}"
        progress=LessonProgress.query.filter_by(user_id=current_user.id,lesson_key=lesson_key).first()
        if not progress:
            progress=LessonProgress(user_id=current_user.id,lesson_key=lesson_key,evidence_count=0); db.session.add(progress); db.session.commit()
        else:
            progress.updated_at=utcnow(); db.session.commit()
        completion=LessonCompletion.query.filter_by(user_id=current_user.id,lesson_id=lesson.id).first()
        exercises=CourseExercise.query.filter_by(lesson_id=lesson.id,published=True).all()
        exercise_attempts={exercise.id:ExerciseAttempt.query.filter_by(user_id=current_user.id,exercise_id=exercise.id).order_by(ExerciseAttempt.created_at.desc()).all() for exercise in exercises}
        video_links=VideoMetadata.query.filter((VideoMetadata.lesson_id==lesson.id)|(VideoMetadata.lesson_id.is_(None)&(VideoMetadata.chapter_id==chapter.id))).all()
        video_ids=[row.video_id for row in video_links]
        videos=VideoResource.query.filter(VideoResource.id.in_(video_ids),VideoResource.active.is_(True),VideoResource.verified.is_(True),VideoResource.verification_status=="verified").all() if video_ids else []
        watched_video_ids={row.video_id for row in VideoWatch.query.filter(VideoWatch.user_id==current_user.id,VideoWatch.video_id.in_(video_ids)).all()} if video_ids else set()
        video_meta={row.video_id:row for row in video_links}
        learning_objectives={row.question_id:row.learning_objective for row in QuestionMetadata.query.filter(QuestionMetadata.question_id.in_(qids)).all()} if qids else {}
        if request.method=="POST":
            details=[]; correct=0
            for q in questions:
                answer=request.form.get("a"+str(q.id)); valid=answer is not None and answer.isdigit() and 0<=int(answer)<len(json.loads(q.options_fr))
                ok=valid and answer==str(q.answer); correct+=int(ok)
                details.append({"question_id":q.id,"topic":chapter.title,"domain":domain,"level":q.level,"prompt":q.prompt_fr,"prompt_ar":q.prompt_ar,"ok":ok,"explanation":q.explanation_fr,"explanation_ar":q.explanation_ar,"answer":q.answer,"options":json.loads(q.options_fr),"options_ar":json.loads(q.options_ar or "[]"),"selected":int(answer) if valid else None})
            if not details: flash("Aucun QCM publié n’est associé à ce chapitre.","error"); return redirect(url_for("lesson",slug=slug,lesson_id=lesson.id))
            db.session.add(Attempt(user_id=current_user.id,mode="qcm",score=correct,total=len(details),details=json.dumps(details,ensure_ascii=False)))
            if len(details)>=3 and correct/len(details)>=0.7:
                progress=progress or LessonProgress(user_id=current_user.id,lesson_key=lesson_key,evidence_count=0); progress.evidence_count+=len(details); db.session.add(progress)
                flash("Palier validé : au moins 70 % sur 3 questions ou plus.","success")
            else: flash("Tentative enregistrée. Pour valider ce palier, il faut au moins 70 % sur 3 questions ou plus.","error")
            db.session.commit(); return redirect(url_for("lesson",slug=slug,lesson_id=lesson.id))
        lesson_list=CurriculumLesson.query.join(CurriculumChapter).join(CurriculumModule).filter(CurriculumModule.subject_id==subject.id,CurriculumModule.published.is_(True),CurriculumChapter.published.is_(True),CurriculumLesson.published.is_(True)).order_by(CurriculumModule.position,CurriculumChapter.position,CurriculumLesson.id).all()
        current_index=next((i for i,item in enumerate(lesson_list) if item.id==lesson.id),0)
        previous_lesson=lesson_list[current_index-1] if current_index>0 else None
        next_lesson=lesson_list[current_index+1] if current_index+1<len(lesson_list) else None
        return render_template("lesson.html",domain=domain,slug=slug,subject=subject,module=module,chapter=chapter,lesson=lesson,objectives=json.loads(lesson.objectives_fr or "[]"),theory_sections=split_lesson_sections(lesson.theory_fr),questions=questions,learning_objectives=learning_objectives,progress=progress,completion=completion,exercises=exercises,exercise_attempts=exercise_attempts,videos=videos,video_meta=video_meta,watched_video_ids=watched_video_ids,previous_lesson=previous_lesson,next_lesson=next_lesson,ai_grading_configured=ai_grading_configured())

    @app.route("/courses/<slug>/lesson/<int:lesson_id>/complete",methods=["POST"])
    @login_required
    def complete_lesson(slug,lesson_id):
        subject=CurriculumSubject.query.filter_by(slug=slug,published=True).first_or_404()
        lesson=CurriculumLesson.query.filter_by(id=lesson_id,published=True).first_or_404()
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id); module=db.session.get(CurriculumModule,chapter.module_id) if chapter else None
        if not module or module.subject_id!=subject.id or not module.published or not chapter.published: abort(404)
        completion=LessonCompletion.query.filter_by(user_id=current_user.id,lesson_id=lesson.id).first()
        if not completion: db.session.add(LessonCompletion(user_id=current_user.id,lesson_id=lesson.id)); db.session.commit()
        flash("Leçon terminée et enregistrée dans ta progression.","success")
        return redirect(url_for("lesson",slug=slug,lesson_id=lesson.id))

    @app.route("/exercise/<int:exercise_id>/attempt",methods=["POST"])
    @login_required
    def submit_exercise_attempt(exercise_id):
        exercise=CourseExercise.query.filter_by(id=exercise_id,published=True).first_or_404()
        lesson=db.session.get(CurriculumLesson,exercise.lesson_id); chapter=db.session.get(CurriculumChapter,lesson.chapter_id) if lesson else None; module=db.session.get(CurriculumModule,chapter.module_id) if chapter else None; subject=db.session.get(CurriculumSubject,module.subject_id) if module else None
        if not lesson or not lesson.published or not chapter or not chapter.published or not module or not module.published or not subject or not subject.published: abort(404)
        submitted=request.form.get("answer","").strip()
        if not submitted or len(submitted)>12000:
            flash("Saisis une réponse de 1 à 12 000 caractères.","error")
            return redirect(url_for("lesson",slug=subject.slug,lesson_id=lesson.id))
        score=None; status="pending_manual"; feedback="Réponse transmise."
        if exercise.exercise_type=="qcm":
            correct=submitted==str(exercise.correct_answer); score=100.0 if correct else 0.0; status="auto_graded"; feedback=exercise.feedback_fr or exercise.solution_fr
        elif exercise.exercise_type=="true_false":
            correct=submitted.lower()==str(exercise.correct_answer).lower(); score=100.0 if correct else 0.0; status="auto_graded"; feedback=exercise.feedback_fr or exercise.solution_fr
        elif exercise.exercise_type=="short_answer":
            accepted=json.loads(exercise.accepted_answers_json or "[]")
            if exercise.correct_answer is not None: accepted.append(exercise.correct_answer)
            correct=short_answer_matches(submitted,accepted)
            score=100.0 if correct else 0.0; status="auto_graded"; feedback=exercise.feedback_fr or exercise.solution_fr
        elif exercise.exercise_type=="open":
            try:
                result=evaluate_open_answer(exercise,submitted,current_app.config.get("EXERCISE_GRADING_EVALUATOR"))
                if result["confidence"] < 0.70:
                    feedback="Évaluation automatique incertaine; réponse transmise à un enseignant pour correction."
                else:
                    score=result["score"]; status="ai_graded"
                    labels={"correct":"Réponse correcte","partially_correct":"Réponse partiellement correcte","incorrect":"Réponse incorrecte"}
                    parts=[labels[result["classification"]]+" — "+result["explanation_fr"]]
                    if result["missing_concepts"]: parts.append("Notions à compléter : "+", ".join(result["missing_concepts"]))
                    if result["expected_answer_fr"]: parts.append("Correction attendue : "+result["expected_answer_fr"])
                    feedback="\n\n".join(parts)
            except RuntimeError as exc:
                if str(exc)=="not_configured": feedback="Aucun évaluateur IA n’est configuré. Ta réponse est en attente de correction manuelle. L’administrateur peut configurer OPENAI_API_KEY et EXERCISE_GRADING_MODEL."
                else: feedback="L’évaluateur IA est indisponible ou sa réponse n’a pas pu être validée. Ta réponse est en attente de correction manuelle."
                current_app.logger.warning("Open exercise evaluation fell back to manual review (%s).",str(exc))
            except (ValueError,TypeError,KeyError) as exc:
                feedback="La réponse de l’évaluateur IA n’a pas pu être validée. Ta réponse est en attente de correction manuelle."
                current_app.logger.warning("Open exercise evaluation output was invalid (%s).",type(exc).__name__)
        else: abort(400)
        attempt=ExerciseAttempt(user_id=current_user.id,exercise_id=exercise.id,submitted_answer=submitted,score=score,status=status,feedback=feedback)
        db.session.add(attempt); db.session.commit()
        # Le résultat est affiché dans la carte de l’exercice, juste sous la réponse.
        return redirect(url_for("lesson",slug=subject.slug,lesson_id=lesson.id)+f"#exercise-{exercise.id}")

    @app.route("/qcm",methods=["GET","POST"])
    @login_required
    def qcm():
        if request.method=="POST":
            ids=session.pop("active_qcm_ids",[])
            if not ids:
                flash("Cette série de QCM a expiré. Lance un nouvel entraînement.","error"); return redirect(url_for("qcm"))
            details=[]; score=0
            for qid in ids:
                q=Question.query.filter_by(id=qid,active=True).first()
                if not q: continue
                selected=request.form.get("a"+str(qid))
                valid=selected is not None and selected.isdigit() and 0<=int(selected)<len(json.loads(q.options_fr))
                ok=valid and selected==str(q.answer); score+=int(ok)
                details.append({"question_id":q.id,"topic":q.topic,"domain":q.domain,"level":q.level,"prompt":q.prompt_fr,"prompt_ar":q.prompt_ar,"ok":ok,"explanation":q.explanation_fr,"explanation_ar":q.explanation_ar,"answer":q.answer,"options":json.loads(q.options_fr),"options_ar":json.loads(q.options_ar or "[]"),"selected":int(selected) if valid else None})
            if not details: flash("Aucune question valide n’a été soumise.","error"); return redirect(url_for("qcm"))
            attempt=Attempt(user_id=current_user.id,mode="qcm",score=score,total=len(details),details=json.dumps(details,ensure_ascii=False))
            db.session.add(attempt); db.session.commit()
            return render_template("attempt_result.html",attempt=attempt,details=details,title="Résultat du QCM")
        domain=request.args.get("domain")
        level=request.args.get("level")
        query=Question.query.filter_by(active=True)
        if domain in {d[0] for d in configured_domains()}: query=query.filter_by(domain=domain)
        if level in QUESTION_LEVELS: query=query.filter_by(level=level)
        topic=request.args.get("topic")
        if topic and len(topic)<=120: query=query.filter_by(topic=topic)
        pool=query.all()
        if request.args.get("retry")=="1":
            wrong_ids=set()
            for attempt in Attempt.query.filter_by(user_id=current_user.id).order_by(Attempt.created_at.desc()).limit(100).all():
                for item in json.loads(attempt.details or "[]"):
                    if not item.get("ok") and item.get("question_id"): wrong_ids.add(item["question_id"])
            retry_pool=[q for q in pool if q.id in wrong_ids]
            qs=random.sample(retry_pool,min(15,len(retry_pool))) if retry_pool else []
        else:
            adaptive=not level
            if adaptive:
                qs,adaptive_summary=adaptive_question_set(current_user.id,domain=domain if domain in {d[0] for d in configured_domains()} else None,topic=topic,limit=15,thresholds=current_app.config["ADAPTIVE_THRESHOLDS"])
            else:
                qs=random.sample(pool,min(15,len(pool))) if pool else []
                adaptive_summary="Mode manuel : le niveau sélectionné filtre les questions."
        topics=sorted({q.topic for q in Question.query.filter_by(active=True).all() if not domain or q.domain==domain})
        session["active_qcm_ids"]=[q.id for q in qs]
        time_limits={row.question_id:row.time_limit_seconds for row in QuestionMetadata.query.filter(QuestionMetadata.time_limit_seconds.isnot(None)).all()}
        learning_objectives={row.question_id:row.learning_objective for row in QuestionMetadata.query.all()}
        return render_template("qcm.html",questions=qs,domains=configured_domains(),topics=topics,selected_domain=domain or "",selected_level=level or "",selected_topic=topic or "",retry=request.args.get("retry")=="1",time_limits=time_limits,learning_objectives=learning_objectives,adaptive=not bool(level) and request.args.get("retry")!="1",adaptive_summary=locals().get("adaptive_summary","Tes erreurs récentes sont placées en priorité lorsque leur niveau correspond."))

    @app.route("/planner")
    @login_required
    def planner():
        plan,personalized=build_study_recommendations(current_user.id)
        return render_template("planner.html",plan=plan,personalized=personalized)

    @app.route("/study",methods=["GET","POST"])
    @login_required
    def study():
        form=StudyForm()
        form.domain.choices=[(name,name) for name,_,_ in configured_domains()]
        goal=StudyGoal.query.filter_by(user_id=current_user.id).first()
        if request.method=="POST" and request.form.get("action")=="goal":
            try: minutes=int(request.form.get("daily_goal",""))
            except ValueError: minutes=0
            if not 15<=minutes<=720: flash("L’objectif doit être compris entre 15 et 720 minutes.","error")
            else:
                goal=goal or StudyGoal(user_id=current_user.id); goal.daily_minutes=minutes; db.session.add(goal); db.session.commit(); flash("Objectif quotidien enregistré.","success")
            return redirect(url_for("study"))
        if form.validate_on_submit():
            s=StudySession(user_id=current_user.id,domain=form.domain.data,minutes=form.minutes.data,studied_on=date.today())
            db.session.add(s); db.session.commit(); flash("Séance enregistrée.","success"); return redirect(url_for("dashboard"))
        sessions=StudySession.query.filter_by(user_id=current_user.id).order_by(StudySession.studied_on.desc(),StudySession.id.desc()).limit(20).all()
        week_total=db.session.query(db.func.coalesce(db.func.sum(StudySession.minutes),0)).filter(StudySession.user_id==current_user.id,StudySession.studied_on>=date.today()-timedelta(days=6)).scalar()
        totals_by_domain=db.session.query(StudySession.domain,db.func.sum(StudySession.minutes)).filter(StudySession.user_id==current_user.id).group_by(StudySession.domain).order_by(db.func.sum(StudySession.minutes).desc()).all()
        return render_template("study.html",form=form,goal=goal,sessions=sessions,week_total=week_total,totals_by_domain=totals_by_domain)

    @app.route("/errors")
    @login_required
    def errors():
        attempts=Attempt.query.filter_by(user_id=current_user.id).order_by(Attempt.created_at.desc()).all()
        errors=[]
        for attempt in attempts:
            for item in json.loads(attempt.details or "[]"):
                if not item.get("ok"): errors.append({**item,"date":attempt.created_at,"mode":attempt.mode})
        saved={b.question_id for b in Bookmark.query.filter_by(user_id=current_user.id).all()}
        return render_template("errors.html",errors=errors,saved=saved)

    @app.route("/bookmark/<int:question_id>",methods=["POST"])
    @login_required
    def bookmark(question_id):
        q=Question.query.filter_by(id=question_id,active=True).first_or_404()
        existing=Bookmark.query.filter_by(user_id=current_user.id,question_id=q.id).first()
        if existing: db.session.delete(existing)
        else: db.session.add(Bookmark(user_id=current_user.id,question_id=q.id))
        db.session.commit(); return redirect(url_for("errors"))

    @app.route("/bookmarks")
    @login_required
    def bookmarks():
        rows=Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.created_at.desc()).all()
        questions=[db.session.get(Question,row.question_id) for row in rows]
        return render_template("bookmarks.html",questions=[q for q in questions if q and q.active])

    @app.route("/language",methods=["POST"])
    @login_required
    def set_language():
        language=request.form.get("language")
        if language not in {"fr","ar"}: abort(400)
        preference=UserPreference.query.filter_by(user_id=current_user.id).first()
        if not preference: preference=UserPreference(user_id=current_user.id)
        preference.language=language; db.session.add(preference); db.session.commit(); session["language"]=language
        return jsonify({"language":language})

    @app.route("/videos")
    @login_required
    def videos():
        resources=VideoResource.query.filter_by(active=True,verified=True).order_by(VideoResource.lesson_key,VideoResource.title).all()
        watched={row.video_id for row in VideoWatch.query.filter_by(user_id=current_user.id).all()}
        video_meta={row.video_id:row for row in VideoMetadata.query.all()}
        video_links={}
        for resource in resources:
            metadata=video_meta.get(resource.id)
            chapter=db.session.get(CurriculumChapter,metadata.chapter_id) if metadata and metadata.chapter_id else None
            lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id,published=True).first() if chapter else None
            module=db.session.get(CurriculumModule,chapter.module_id) if chapter else None
            subject=db.session.get(CurriculumSubject,module.subject_id) if module else None
            slug=subject.slug if subject else COURSE_SLUGS.get(resource.lesson_key)
            video_links[resource.id]={"lesson_id":lesson.id if lesson else None,"slug":slug,"chapter":chapter.title if chapter else None}
        mastery=calculate_mastery(current_user.id)
        assessed=[d for d in configured_domains() if mastery[d[0]]["percent"] is not None]
        recommended_domain=min(assessed,key=lambda d:mastery[d[0]]["percent"])[0] if assessed else None
        recommended_subject=CurriculumSubject.query.filter_by(name=recommended_domain,published=True).first() if recommended_domain else None
        recommended_slug=recommended_subject.slug if recommended_subject else COURSE_SLUGS.get(recommended_domain)
        return render_template("videos.html",resources=resources,watched=watched,recommended_slug=recommended_slug,video_meta=video_meta,video_links=video_links)

    @app.route("/videos/<int:video_id>/watched",methods=["POST"])
    @login_required
    def mark_video_watched(video_id):
        video=VideoResource.query.filter_by(id=video_id,active=True,verified=True).first_or_404()
        existing=VideoWatch.query.filter_by(user_id=current_user.id,video_id=video.id).first()
        if existing: db.session.delete(existing)
        else: db.session.add(VideoWatch(user_id=current_user.id,video_id=video.id))
        db.session.commit()
        next_url=request.form.get("next","")
        parsed=urlparse(next_url)
        if not next_url.startswith("/") or next_url.startswith("//") or parsed.netloc: next_url=url_for("videos")
        return redirect(next_url)

    @app.route("/admin/curriculum",methods=["GET","POST"])
    @login_required
    def admin_curriculum():
        if current_user.role!="admin": abort(403)
        if request.method=="POST":
            action=request.form.get("action","")
            def required(name,limit=200):
                value=request.form.get(name,"").strip()
                return value[:limit] if value else ""
            def position():
                try: return max(0,min(10000,int(request.form.get("position","0"))))
                except (TypeError,ValueError): return None
            def entity(model): return db.session.get(model,request.form.get("id",type=int))
            def exercise_fields():
                title=required("title",180); prompt=required("prompt_fr",5000); solution=required("solution_fr",8000); level=request.form.get("level",""); kind=request.form.get("exercise_type","open")
                options=[request.form.get(f"option_{i}","").strip()[:500] for i in range(4)]
                if kind not in {"qcm","true_false","short_answer","open"} or not title or not prompt or not solution or level not in {"Facile","Moyen","Difficile",*EXERCISE_LEVELS}: raise ValueError()
                correct=None; accepted=[]
                if kind=="qcm":
                    try: correct=int(request.form.get("correct_answer","-1"))
                    except ValueError: correct=-1
                    if any(not option for option in options) or len(set(options))!=4 or correct not in range(4): raise ValueError()
                elif kind=="true_false":
                    correct=request.form.get("correct_answer","")
                    if correct not in {"true","false"}: raise ValueError()
                elif kind=="short_answer":
                    accepted=[line.strip()[:200] for line in request.form.get("accepted_answers","").splitlines() if line.strip()]
                    if not accepted: raise ValueError()
                return {"title":title,"prompt_fr":prompt,"prompt_ar":required("prompt_ar",5000),"solution_fr":solution,"solution_ar":required("solution_ar",8000),"exercise_type":kind,"options_json":json.dumps(options,ensure_ascii=False) if kind=="qcm" else "[]","correct_answer":str(correct) if correct is not None else None,"accepted_answers_json":json.dumps(accepted,ensure_ascii=False),"feedback_fr":required("feedback_fr",3000),"grading_guide_fr":required("grading_guide_fr",4000),"learning_objective_fr":required("learning_objective_fr",400),"level":level}
            try:
                if action=="create_subject":
                    name=required("name",100); slug=required("slug",100).lower(); category=request.form.get("category",""); weight=int(request.form.get("weight","-1"))
                    official=next((row for row in DOMAINS if row[0]==name),None)
                    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or not category or len(category)>60 or not 0<=weight<=100 or not name or official and (COURSE_SLUGS.get(name)!=slug or weight!=official[1] or category!=official[2]): raise ValueError()
                    if CurriculumSubject.query.filter((CurriculumSubject.slug==slug)|(CurriculumSubject.name==name)).first(): flash("Cette matière existe déjà.","error")
                    else: db.session.add(CurriculumSubject(name=name,slug=slug,category=category,weight=weight,position=position() or 0)); db.session.commit(); flash("Matière créée.","success")
                elif action in {"edit_subject","toggle_subject","delete_subject"}:
                    subject=entity(CurriculumSubject)
                    if not subject: abort(404)
                    if action=="toggle_subject": subject.published=not subject.published
                    elif action=="delete_subject":
                        if CurriculumModule.query.filter_by(subject_id=subject.id).first(): flash("Supprime d’abord ses modules avant de supprimer cette matière.","error")
                        else: db.session.delete(subject)
                    else:
                        official=next((row for row in DOMAINS if row[0]==subject.name),None)
                        new_category=request.form.get("category",subject.category); new_weight=int(request.form.get("weight",subject.weight))
                        if official and (new_category!=official[2] or new_weight!=official[1]) or not official and (not new_category or len(new_category)>60 or not 0<=new_weight<=100): raise ValueError()
                        subject.category=new_category; subject.weight=new_weight
                    db.session.commit(); flash("Matière mise à jour.","success")
                elif action=="create_module":
                    subject=db.session.get(CurriculumSubject,request.form.get("subject_id",type=int)); title=required("title",160); order=position()
                    if not subject or not title or order is None: raise ValueError()
                    db.session.add(CurriculumModule(subject_id=subject.id,title=title,position=order)); db.session.commit(); flash("Module créé.","success")
                elif action in {"edit_module","toggle_module","delete_module"}:
                    item=entity(CurriculumModule)
                    if not item: abort(404)
                    if action=="toggle_module": item.published=not item.published
                    elif action=="delete_module":
                        if CurriculumChapter.query.filter_by(module_id=item.id).first(): flash("Supprime d’abord les chapitres de ce module.","error")
                        else: db.session.delete(item)
                    else:
                        item.title=required("title",160); item.position=position()
                        if not item.title or item.position is None: raise ValueError()
                    db.session.commit(); flash("Module mis à jour.","success")
                elif action=="create_chapter":
                    module=db.session.get(CurriculumModule,request.form.get("module_id",type=int)); title=required("title",160); order=position()
                    if not module or not title or order is None: raise ValueError()
                    db.session.add(CurriculumChapter(module_id=module.id,title=title,position=order)); db.session.commit(); flash("Chapitre créé.","success")
                elif action in {"edit_chapter","toggle_chapter","delete_chapter"}:
                    item=entity(CurriculumChapter)
                    if not item: abort(404)
                    if action=="toggle_chapter": item.published=not item.published
                    elif action=="delete_chapter":
                        if CurriculumLesson.query.filter_by(chapter_id=item.id).first() or QuestionMetadata.query.filter_by(chapter_id=item.id).first() or VideoMetadata.query.filter_by(chapter_id=item.id).first(): flash("Ce chapitre est encore utilisé. Déplace ou supprime d’abord les contenus associés.","error")
                        else: db.session.delete(item)
                    else:
                        item.title=required("title",160); item.position=position()
                        if not item.title or item.position is None: raise ValueError()
                    db.session.commit(); flash("Chapitre mis à jour.","success")
                elif action=="create_lesson":
                    chapter=db.session.get(CurriculumChapter,request.form.get("chapter_id",type=int)); title=required("title",200); theory=required("theory_fr",12000); darija=required("theory_ar",12000)
                    if not chapter or not title or not theory or not darija: raise ValueError()
                    lesson=CurriculumLesson(chapter_id=chapter.id,title=title,objectives_fr=json.dumps([line.strip() for line in request.form.get("objectives_fr","").splitlines() if line.strip()],ensure_ascii=False),prerequisites_fr=required("prerequisites_fr",3000),theory_fr=theory,theory_ar=darija,example_fr=required("example_fr",5000),code_example=request.form.get("code_example","")[:8000],exercise_fr=required("exercise_fr",5000),solution_fr=required("solution_fr",8000),summary_fr=required("summary_fr",3000),revision_fr=required("revision_fr",3000),published=False)
                    db.session.add(lesson); db.session.commit(); flash("Leçon créée en brouillon. Publie-la après relecture.","success")
                elif action in {"edit_lesson","toggle_lesson","delete_lesson"}:
                    item=entity(CurriculumLesson)
                    if not item: abort(404)
                    if action=="toggle_lesson": item.published=not item.published
                    elif action=="delete_lesson":
                        if CourseExercise.query.filter_by(lesson_id=item.id).first() or LessonProgress.query.filter_by(lesson_key=f"lesson:{item.id}").first() or LessonCompletion.query.filter_by(lesson_id=item.id).first(): flash("Cette leçon est liée à des exercices ou à une progression. Dépublie-la pour préserver l’historique.","error")
                        else: db.session.delete(item)
                    else:
                        title=required("title",200); theory=required("theory_fr",12000); darija=required("theory_ar",12000)
                        if not title or not theory or not darija: raise ValueError()
                        item.title=title; item.objectives_fr=json.dumps([line.strip() for line in request.form.get("objectives_fr","").splitlines() if line.strip()],ensure_ascii=False); item.prerequisites_fr=required("prerequisites_fr",3000); item.theory_fr=theory; item.theory_ar=darija; item.example_fr=required("example_fr",5000); item.code_example=request.form.get("code_example","")[:8000]; item.exercise_fr=required("exercise_fr",5000); item.solution_fr=required("solution_fr",8000); item.summary_fr=required("summary_fr",3000); item.revision_fr=required("revision_fr",3000)
                    db.session.commit(); flash("Leçon mise à jour.","success")
                elif action=="create_exercise":
                    lesson=db.session.get(CurriculumLesson,request.form.get("lesson_id",type=int)); fields=exercise_fields()
                    if not lesson: raise ValueError()
                    db.session.add(CourseExercise(lesson_id=lesson.id,**fields,published=False)); db.session.commit(); flash("Exercice créé en brouillon.","success")
                elif action in {"edit_exercise","toggle_exercise","delete_exercise"}:
                    item=entity(CourseExercise)
                    if not item: abort(404)
                    if action=="toggle_exercise": item.published=not item.published
                    elif action=="delete_exercise":
                        if ExerciseAttempt.query.filter_by(exercise_id=item.id).first(): flash("Cet exercice possède un historique de tentatives. Dépublie-le pour conserver les données.","error")
                        else: db.session.delete(item)
                    else:
                        if ExerciseAttempt.query.filter_by(exercise_id=item.id).first():
                            flash("Cet exercice possède un historique de tentatives. Crée une nouvelle version pour préserver les corrections existantes.","error")
                            return redirect(url_for("admin_curriculum"))
                        for key,value in exercise_fields().items(): setattr(item,key,value)
                    db.session.commit(); flash("Exercice mis à jour.","success")
                else: abort(400)
            except (TypeError,ValueError):
                db.session.rollback(); flash("Informations invalides. Vérifie les champs requis et leurs limites.","error")
            return redirect(url_for("admin_curriculum"))
        subjects=CurriculumSubject.query.order_by(CurriculumSubject.position).all()
        modules=CurriculumModule.query.order_by(CurriculumModule.subject_id,CurriculumModule.position).all()
        chapters=CurriculumChapter.query.order_by(CurriculumChapter.module_id,CurriculumChapter.position).all()
        lessons=CurriculumLesson.query.order_by(CurriculumLesson.id.desc()).all()
        exercises=CourseExercise.query.order_by(CourseExercise.id.desc()).all()
        return render_template("admin_curriculum.html",subjects=subjects,modules=modules,chapters=chapters,lessons=lessons,exercises=exercises)

    @app.route("/admin/exercise-attempts",methods=["GET","POST"])
    @login_required
    def admin_exercise_attempts():
        if current_user.role!="admin": abort(403)
        if request.method=="POST":
            attempt=db.session.get(ExerciseAttempt,request.form.get("attempt_id",type=int))
            try: score=float(request.form.get("score",""))
            except (TypeError,ValueError): score=-1
            feedback=request.form.get("feedback","").strip()[:2000]
            exercise=db.session.get(CourseExercise,attempt.exercise_id) if attempt else None
            if not attempt or attempt.status!="pending_manual" or not exercise or exercise.exercise_type!="open" or not 0<=score<=100 or not feedback:
                flash("Évaluation invalide : une note de 0 à 100 et un commentaire sont requis.","error")
            else:
                attempt.score=score; attempt.feedback=feedback; attempt.status="manually_graded"; attempt.evaluated_by=current_user.id; attempt.evaluated_at=utcnow()
                db.session.commit(); flash("Correction enregistrée pour l’apprenant.","success")
            return redirect(url_for("admin_exercise_attempts"))
        pending=ExerciseAttempt.query.filter_by(status="pending_manual").order_by(ExerciseAttempt.created_at.asc()).limit(200).all()
        details=[]
        for attempt in pending:
            exercise=db.session.get(CourseExercise,attempt.exercise_id); user=db.session.get(User,attempt.user_id)
            details.append({"attempt":attempt,"exercise":exercise,"user":user})
        return render_template("admin_exercise_attempts.html",pending=details,ai_grading_configured=ai_grading_configured())

    @app.route("/admin/quality")
    @login_required
    def admin_quality():
        if current_user.role!="admin": abort(403)
        subject_id=request.args.get("subject",type=int); chapter_id=request.args.get("chapter",type=int); status=request.args.get("status","")
        query=CurriculumLesson.query.join(CurriculumChapter).join(CurriculumModule).join(CurriculumSubject).order_by(CurriculumSubject.position,CurriculumModule.position,CurriculumChapter.position,CurriculumLesson.id)
        if subject_id: query=query.filter(CurriculumSubject.id==subject_id)
        if chapter_id: query=query.filter(CurriculumChapter.id==chapter_id)
        rows=[]
        for lesson in query.all():
            chapter=db.session.get(CurriculumChapter,lesson.chapter_id)
            exercises=CourseExercise.query.filter_by(lesson_id=lesson.id,published=True).all()
            videos=VideoMetadata.query.join(VideoResource,VideoMetadata.video_id==VideoResource.id).filter(VideoResource.active.is_(True),VideoResource.verified.is_(True),VideoResource.verification_status=="verified").filter((VideoMetadata.lesson_id==lesson.id)|((VideoMetadata.lesson_id.is_(None))&(VideoMetadata.chapter_id==lesson.chapter_id))).all()
            rows.append(audit_lesson(lesson,chapter,exercises,len(videos)))
        if status=="complete": rows=[r for r in rows if r["complete"]]
        elif status=="incomplete": rows=[r for r in rows if not r["complete"]]
        elif status=="review": rows=[r for r in rows if r["expert_review"]]
        chapters=CurriculumChapter.query.join(CurriculumModule).order_by(CurriculumChapter.title).all()
        subjects=CurriculumSubject.query.order_by(CurriculumSubject.position).all()
        counts={"complete":sum(r["complete"] for r in rows),"incomplete":sum(not r["complete"] for r in rows),"review":sum(r["expert_review"] for r in rows),"missing_exercises":sum(not r["fields"]["exercices progressifs"] for r in rows),"missing_verified_video":sum(not r["fields"]["vidéo dédiée vérifiée"] for r in rows),"pending_videos":VideoResource.query.filter_by(verification_status="pending").count(),"rejected_videos":VideoResource.query.filter_by(verification_status="rejected").count(),"questions":Question.query.filter_by(active=True).count(),"attempts":Attempt.query.count()+ExerciseAttempt.query.count()}
        return render_template("admin_quality.html",rows=rows,counts=counts,subjects=subjects,chapters=chapters,subject_id=subject_id,chapter_id=chapter_id,status=status)

    @app.route("/admin/videos",methods=["GET","POST"])
    @login_required
    def admin_videos():
        if current_user.role!="admin": abort(403)
        if request.method=="POST":
            action=request.form.get("action")
            if action=="create":
                title=request.form.get("title","").strip(); channel=request.form.get("channel","").strip()
                lesson_key=request.form.get("lesson_key",""); language=request.form.get("language",""); description=request.form.get("description","").strip()[:4000]
                raw_url=request.form.get("url","").strip(); video_id=extract_youtube_video_id(raw_url) or ""
                try: duration=int(request.form.get("duration_minutes") or 0) or None
                except ValueError: duration=-1
                thumbnail=request.form.get("thumbnail_url","").strip() or None; thumb_parsed=urlparse(thumbnail or "")
                thumbnail_ok=not thumbnail or (thumb_parsed.scheme=="https" and bool(thumb_parsed.netloc) and not thumb_parsed.username and not thumb_parsed.password)
                subject=CurriculumSubject.query.filter_by(slug=lesson_key).first(); lesson=db.session.get(CurriculumLesson,request.form.get("lesson_id",type=int)) if request.form.get("lesson_id",type=int) else None; chapter=db.session.get(CurriculumChapter,lesson.chapter_id) if lesson else (db.session.get(CurriculumChapter,request.form.get("chapter_id",type=int)) if request.form.get("chapter_id",type=int) else None)
                chapter_module=db.session.get(CurriculumModule,chapter.module_id) if chapter else None
                if (not title or not channel or not subject or language not in {"Français","العربية / Darija","Arabe"} or not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id or "") or duration is not None and not 1<=duration<=600 or not thumbnail_ok or lesson and (not chapter_module or chapter_module.subject_id!=subject.id) or not lesson and chapter and (not chapter_module or chapter_module.subject_id!=subject.id)):
                    flash("Ressource invalide : vérifie le titre, la chaîne, le lien YouTube, la matière, la langue et la durée.","error")
                elif VideoResource.query.filter_by(video_id=video_id).first(): flash("Cette vidéo est déjà enregistrée.","error")
                else:
                    manually_verified=request.form.get("verified")=="yes"
                    resource=VideoResource(title=title[:200],channel=channel[:160],video_id=video_id,language=language,lesson_key=lesson_key,duration_minutes=duration,verified=manually_verified,verification_status="verified" if manually_verified else "pending",verified_at=utcnow() if manually_verified else None,created_by=current_user.id)
                    db.session.add(resource); db.session.flush(); db.session.add(VideoMetadata(video_id=resource.id,description=description,chapter_id=chapter.id if chapter else None,lesson_id=lesson.id if lesson else None,thumbnail_url=thumbnail[:500] if thumbnail else None)); db.session.commit(); flash("Ressource ajoutée en attente de vérification.","success")
            elif action=="toggle":
                resource=db.session.get(VideoResource,request.form.get("video_id",type=int))
                if resource:
                    resource.active=not resource.active; db.session.commit(); flash("Statut de la vidéo mis à jour.","success")
            elif action in {"verify","reject","unavailable","pending"}:
                resource=db.session.get(VideoResource,request.form.get("video_id",type=int))
                if resource:
                    resource.verification_status={"verify":"verified","reject":"rejected","unavailable":"unavailable","pending":"pending"}[action]
                    resource.verified=action=="verify"; resource.verified_at=utcnow() if action=="verify" else None
                    db.session.commit(); flash("Statut de vérification mis à jour.","success")
            elif action=="delete":
                resource=db.session.get(VideoResource,request.form.get("video_id",type=int))
                if not resource: abort(404)
                if VideoWatch.query.filter_by(video_id=resource.id).first(): flash("Cette vidéo a déjà des suivis de visionnage. Désactive-la pour conserver l’historique.","error")
                else:
                    VideoMetadata.query.filter_by(video_id=resource.id).delete(); db.session.delete(resource); db.session.commit(); flash("Ressource supprimée.","success")
            elif action=="edit":
                resource=db.session.get(VideoResource,request.form.get("video_id",type=int))
                title=request.form.get("title","").strip(); channel=request.form.get("channel","").strip()
                lesson_key=request.form.get("lesson_key",""); language=request.form.get("language",""); description=request.form.get("description","").strip()[:4000]
                raw_url=request.form.get("url","").strip(); video_id=extract_youtube_video_id(raw_url) or ""
                try: duration=int(request.form.get("duration_minutes") or 0) or None
                except ValueError: duration=-1
                thumbnail=request.form.get("thumbnail_url","").strip() or None; thumb_parsed=urlparse(thumbnail or ""); lesson=db.session.get(CurriculumLesson,request.form.get("lesson_id",type=int)) if request.form.get("lesson_id",type=int) else None; chapter=db.session.get(CurriculumChapter,lesson.chapter_id) if lesson else (db.session.get(CurriculumChapter,request.form.get("chapter_id",type=int)) if request.form.get("chapter_id",type=int) else None); subject=CurriculumSubject.query.filter_by(slug=lesson_key).first(); chapter_module=db.session.get(CurriculumModule,chapter.module_id) if chapter else None
                thumbnail_ok=not thumbnail or (thumb_parsed.scheme=="https" and bool(thumb_parsed.netloc) and not thumb_parsed.username and not thumb_parsed.password)
                duplicate=VideoResource.query.filter(VideoResource.video_id==video_id,VideoResource.id!=getattr(resource,"id",None)).first() if video_id else None
                if resource and title and channel and subject and language in {"Français","العربية / Darija","Arabe"} and re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id or "") and not duplicate and (duration is None or 1<=duration<=600) and thumbnail_ok and (not chapter or chapter_module and chapter_module.subject_id==subject.id):
                    previous_metadata=VideoMetadata.query.filter_by(video_id=resource.id).first()
                    metadata_changed=(video_id!=resource.video_id or title[:200]!=resource.title or channel[:160]!=resource.channel or lesson_key!=resource.lesson_key or language!=resource.language or duration!=resource.duration_minutes or description!=(previous_metadata.description if previous_metadata else "") or (thumbnail[:500] if thumbnail else None)!=(previous_metadata.thumbnail_url if previous_metadata else None) or (chapter.id if chapter else None)!=(previous_metadata.chapter_id if previous_metadata else None) or (lesson.id if lesson else None)!=(previous_metadata.lesson_id if previous_metadata else None))
                    if metadata_changed:
                        resource.verified=False; resource.verification_status="pending"; resource.verified_at=None
                    resource.title=title[:200]; resource.channel=channel[:160]; resource.video_id=video_id; resource.lesson_key=lesson_key; resource.language=language; resource.duration_minutes=duration
                    metadata=VideoMetadata.query.filter_by(video_id=resource.id).first() or VideoMetadata(video_id=resource.id); metadata.description=description; metadata.chapter_id=chapter.id if chapter else None; metadata.lesson_id=lesson.id if lesson else None; metadata.thumbnail_url=thumbnail[:500] if thumbnail else None; db.session.add(metadata); db.session.commit(); flash("Ressource vidéo modifiée; elle reste en attente si elle n’est pas validée.","success")
                else: flash("Modifications invalides.","error")
            else: abort(400)
            return redirect(url_for("admin_videos"))
        resources=VideoResource.query.order_by(VideoResource.created_at.desc()).all()
        metadata={row.video_id:row for row in VideoMetadata.query.all()}
        subjects=CurriculumSubject.query.order_by(CurriculumSubject.position).all()
        chapters=CurriculumChapter.query.join(CurriculumModule).join(CurriculumSubject).order_by(CurriculumSubject.position,CurriculumModule.position,CurriculumChapter.position).all()
        lessons=CurriculumLesson.query.order_by(CurriculumLesson.id).all()
        return render_template("admin_videos.html",resources=resources,course_slugs={s.name:s.slug for s in subjects},chapters=chapters,lessons=lessons,metadata=metadata)

    @app.route("/exam",methods=["GET","POST"])
    @login_required
    def exam():
        if request.method=="POST":
            issued_ids=session.pop("active_exam_ids",[])
            started=session.pop("active_exam_started",None)
            run_id=session.pop("active_exam_run",None)
            if not issued_ids or not started or not run_id or request.form.get("run_id")!=run_id:
                flash("Cette session d’examen a expiré. Lance un nouvel examen blanc.","error"); return redirect(url_for("exam"))
            elapsed_seconds=max(0,int(time.time()-started))
            ids=issued_ids
            details=[]; score=0
            for qid in ids:
                q=Question.query.filter_by(id=qid,active=True).first()
                if q:
                    selected=request.form.get("a"+str(qid)) if elapsed_seconds<=current_app.config["EXAM_DURATION_MINUTES"]*60 else None; valid=selected is not None and selected.isdigit() and 0<=int(selected)<len(json.loads(q.options_fr)); ok=valid and selected==str(q.answer); score+=int(ok)
                    details.append({"question_id":q.id,"topic":q.topic,"domain":q.domain,"level":q.level,"prompt":q.prompt_fr,"prompt_ar":q.prompt_ar,"ok":ok,"explanation":q.explanation_fr,"explanation_ar":q.explanation_ar,"answer":q.answer,"options":json.loads(q.options_fr),"options_ar":json.loads(q.options_ar or "[]"),"selected":int(selected) if valid else None})
            if not details: flash("Aucune question valide n’a été soumise.","error"); return redirect(url_for("exam"))
            duration=min(current_app.config["EXAM_DURATION_MINUTES"],elapsed_seconds//60)
            attempt=Attempt(user_id=current_user.id,mode="exam",score=score,total=len(details),details=json.dumps(details,ensure_ascii=False),duration_minutes=duration)
            db.session.add(attempt); db.session.commit()
            return render_template("attempt_result.html",attempt=attempt,details=details,title="Résultat de l’examen blanc")
        qs=Question.query.filter_by(active=True).all()
        # Largest-remainder quotas preserve the configured curriculum proportions where available.
        targets={name:30*weight/100 for name,weight,_ in DOMAINS}
        quotas={name:int(targets[name]) for name,_,_ in DOMAINS}
        for name in sorted(targets,key=lambda n:targets[n]-int(targets[n]),reverse=True)[:30-sum(quotas.values())]: quotas[name]+=1
        available={name:[q for q in qs if q.domain==name] for name,_,_ in DOMAINS}
        selected=[]; selected_by_domain={name:0 for name,_,_ in DOMAINS}
        for name,_,_ in DOMAINS:
            take=min(len(available[name]),quotas[name])
            chosen,_=adaptive_question_set(current_user.id,domain=name,limit=take,thresholds=current_app.config["ADAPTIVE_THRESHOLDS"]) if take else ([],"")
            selected.extend(chosen); selected_by_domain[name]=len(chosen)
        remaining=30-len(selected); already={q.id for q in selected}
        mastery=calculate_mastery(current_user.id)
        for name,_,_ in DOMAINS:
            stage=adaptive_level_for_score(mastery[name]["percent"],current_app.config["ADAPTIVE_THRESHOLDS"]) if mastery[name]["percent"] is not None else None
            allowed=ADAPTIVE_QUESTION_LEVELS.get(stage,{"Facile","Moyen","Débutant","Élémentaire","Intermédiaire"})
            available[name]=[q for q in available[name] if q.level in allowed]
        while remaining>0:
            eligible=[name for name in available if any(q.id not in already for q in available[name])]
            if not eligible: break
            name=max(eligible,key=lambda n:targets[n]/(selected_by_domain[n]+1))
            candidate=random.choice([q for q in available[name] if q.id not in already])
            selected.append(candidate); already.add(candidate.id); selected_by_domain[name]+=1; remaining-=1
        random.shuffle(selected)
        selected=selected[:30]
        session["active_exam_ids"]=[q.id for q in selected]
        session["active_exam_started"]=int(time.time())
        session["active_exam_run"]=secrets.token_urlsafe(12)
        time_limits={row.question_id:row.time_limit_seconds for row in QuestionMetadata.query.filter(QuestionMetadata.time_limit_seconds.isnot(None)).all()}
        learning_objectives={row.question_id:row.learning_objective for row in QuestionMetadata.query.all()}
        return render_template("exam.html",questions=selected,run_id=session["active_exam_run"],started_at=session["active_exam_started"],time_limits=time_limits,learning_objectives=learning_objectives,duration_minutes=current_app.config["EXAM_DURATION_MINUTES"])

    @app.route("/admin",methods=["GET","POST"])
    @login_required
    def admin():
        if current_user.role!="admin": abort(403)
        if request.method=="POST":
            action=request.form.get("action")
            if action=="toggle_question":
                question=db.session.get(Question,request.form.get("question_id",type=int))
                if question:
                    question.active=not question.active; db.session.commit(); flash("Statut de la question mis à jour.","success")
                else: flash("Question introuvable.","error")
            elif action=="delete_question":
                question=db.session.get(Question,request.form.get("question_id",type=int))
                if not question: abort(404)
                used=Bookmark.query.filter_by(question_id=question.id).first()
                if not used:
                    for attempt in Attempt.query.all():
                        if any(item.get("question_id")==question.id for item in json.loads(attempt.details or "[]")):
                            used=True; break
                if used: flash("Cette question figure dans un historique ou des favoris. Désactive-la pour préserver ces données.","error")
                else:
                    QuestionMetadata.query.filter_by(question_id=question.id).delete(); db.session.delete(question); db.session.commit(); flash("Question supprimée.","success")
            elif action=="set_role":
                user=db.session.get(User,request.form.get("user_id",type=int)); role=request.form.get("role")
                if user and user.id!=current_user.id and role in {"student","admin"}:
                    user.role=role; db.session.commit(); flash("Rôle du compte mis à jour.","success")
                else: flash("Modification de rôle invalide.","error")
            elif action in {"create_question","edit_question"}:
                domain=request.form.get("domain",""); level=request.form.get("level","")
                options=[request.form.get(f"option_{i}","").strip() for i in range(4)]
                try: answer=int(request.form.get("answer","-1"))
                except ValueError: answer=-1
                prompt=request.form.get("prompt_fr","").strip(); topic=request.form.get("topic","").strip(); explanation=request.form.get("explanation_fr","").strip()
                chapter_id=request.form.get("chapter_id",type=int); chapter=db.session.get(CurriculumChapter,chapter_id) if chapter_id else None
                chapter_subject=db.session.get(CurriculumModule,chapter.module_id) if chapter else None
                subject_for_chapter=db.session.get(CurriculumSubject,chapter_subject.subject_id) if chapter_subject else None
                learning_objective=request.form.get("learning_objective","").strip()[:400]
                try: time_limit=int(request.form.get("time_limit_seconds") or 0) or None
                except ValueError: time_limit=-1
                question=db.session.get(Question,request.form.get("question_id",type=int)) if action=="edit_question" else Question()
                if action=="edit_question" and not question: abort(404)
                duplicate_query=Question.query.filter_by(domain=domain,prompt_fr=prompt)
                if question: duplicate_query=duplicate_query.filter(Question.id!=question.id)
                duplicate=duplicate_query.first()
                if duplicate or domain not in {d[0] for d in configured_domains()} or level not in QUESTION_LEVELS or not topic or not prompt or not explanation or not learning_objective or not chapter or not subject_for_chapter or subject_for_chapter.name!=domain or any(not x for x in options) or len(set(options))<4 or answer not in range(4) or time_limit is not None and not 5<=time_limit<=7200:
                    flash("Question invalide : vérifie matière, chapitre, objectif pédagogique, niveau, 4 choix distincts, réponse, correction et durée.","error")
                else:
                    question.domain=domain; question.topic=topic[:120]; question.level=level; question.prompt_fr=prompt; question.prompt_ar=request.form.get("prompt_ar","").strip(); question.options_fr=json.dumps(options,ensure_ascii=False); question.options_ar=json.dumps([request.form.get(f"option_ar_{i}","").strip() for i in range(4)],ensure_ascii=False); question.answer=answer; question.explanation_fr=explanation; question.explanation_ar=request.form.get("explanation_ar","").strip()
                    if action=="create_question": question.active=False; db.session.add(question); db.session.flush()
                    metadata=QuestionMetadata.query.filter_by(question_id=question.id).first() or QuestionMetadata(question_id=question.id)
                    associated_lesson=CurriculumLesson.query.filter_by(chapter_id=chapter_id).first()
                    metadata.chapter_id=chapter_id; metadata.lesson_id=associated_lesson.id if associated_lesson else None; metadata.time_limit_seconds=time_limit
                    metadata.learning_objective=learning_objective
                    db.session.add(metadata); db.session.commit(); flash("Question enregistrée.","success")
            else: abort(400)
            return redirect(url_for("admin"))
        users=User.query.count(); questions=Question.query.count(); attempts=Attempt.query.count()
        user_rows=User.query.order_by(User.created_at.desc()).limit(100).all()
        question_rows=Question.query.order_by(Question.domain,Question.topic).all()
        chapters=CurriculumChapter.query.join(CurriculumModule).join(CurriculumSubject).order_by(CurriculumSubject.position,CurriculumModule.position,CurriculumChapter.position).all()
        question_meta={row.question_id:row for row in QuestionMetadata.query.all()}
        published_lesson_rows=CurriculumLesson.query.join(CurriculumChapter).join(CurriculumModule).join(CurriculumSubject).filter(CurriculumLesson.published.is_(True),CurriculumChapter.published.is_(True),CurriculumModule.published.is_(True),CurriculumSubject.published.is_(True)).all()
        published_lessons=len(published_lesson_rows)
        lesson_exercise_counts={lesson_id:count for lesson_id,count in db.session.query(CourseExercise.lesson_id,func.count(CourseExercise.id)).filter(CourseExercise.published.is_(True)).group_by(CourseExercise.lesson_id).all()}
        chapter_question_counts={chapter_id:count for chapter_id,count in db.session.query(QuestionMetadata.chapter_id,func.count(QuestionMetadata.question_id)).join(Question,Question.id==QuestionMetadata.question_id).filter(Question.active.is_(True),QuestionMetadata.chapter_id.isnot(None)).group_by(QuestionMetadata.chapter_id).all()}
        incomplete_lesson_rows=[lesson for lesson in published_lesson_rows if len(lesson.theory_fr or "")<700 or not lesson.objectives_fr or not lesson.prerequisites_fr or not lesson.example_fr or not lesson.summary_fr or not lesson.revision_fr or lesson_exercise_counts.get(lesson.id,0)<2 or chapter_question_counts.get(lesson.chapter_id,0)<3]
        incomplete_lessons=len(incomplete_lesson_rows)
        published_chapter_ids={row.chapter_id for row in VideoMetadata.query.join(VideoResource,VideoResource.id==VideoMetadata.video_id).filter(VideoResource.active.is_(True),VideoResource.verified.is_(True),VideoMetadata.chapter_id.isnot(None)).all()}
        lesson_chapters={row.chapter_id for row in published_lesson_rows}
        missing_video_lessons=sum(1 for chapter_id in lesson_chapters if chapter_id not in published_chapter_ids)
        incomplete_lesson_rows=[lesson for lesson in published_lesson_rows if len(lesson.theory_fr or "")<700 or not lesson.objectives_fr or not lesson.prerequisites_fr or not lesson.example_fr or not lesson.summary_fr or not lesson.revision_fr or lesson_exercise_counts.get(lesson.id,0)<2 or chapter_question_counts.get(lesson.chapter_id,0)<3 or lesson.chapter_id not in published_chapter_ids]
        incomplete_lessons=len(incomplete_lesson_rows)
        questions_by_domain={name:Question.query.filter_by(domain=name,active=True).count() for name,_,_ in configured_domains()}
        questions_by_level={level:Question.query.filter_by(level=level,active=True).count() for level in QUESTION_LEVELS}
        unpublished_lessons=CurriculumLesson.query.filter_by(published=False).count()
        questions_requiring_review=0
        for question in Question.query.filter_by(active=True).all():
            metadata=question_meta.get(question.id)
            try: options=json.loads(question.options_fr or "[]")
            except (TypeError,ValueError): options=[]
            if not metadata or not metadata.chapter_id or not metadata.learning_objective or len(options)!=4 or len(set(options))!=4 or question.answer not in range(4) or len((question.explanation_fr or "").strip())<40:
                questions_requiring_review+=1
        unpublished=(CurriculumSubject.query.filter_by(published=False).count()+CurriculumModule.query.filter_by(published=False).count()+CurriculumChapter.query.filter_by(published=False).count()+CurriculumLesson.query.filter_by(published=False).count()+CourseExercise.query.filter_by(published=False).count()+Question.query.filter_by(active=False).count())
        return render_template("admin.html",users=users,questions=questions,attempts=attempts,user_rows=user_rows,question_rows=question_rows,domains=configured_domains(),chapters=chapters,question_meta=question_meta,published_lessons=published_lessons,unpublished_lessons=unpublished_lessons,incomplete_lessons=incomplete_lessons,incomplete_lesson_rows=incomplete_lesson_rows,questions_requiring_review=questions_requiring_review,missing_video_lessons=missing_video_lessons,questions_by_domain=questions_by_domain,questions_by_level=questions_by_level,unpublished=unpublished)

app=create_app()
if os.environ.get("AUTO_SEED_CONTENT","1" if os.environ.get("APP_ENV","development").lower() in {"development","dev"} else "0")=="1":
    with app.app_context(): seed_questions()

@app.cli.command("seed-content")
def seed_content_command():
    """Add built-in educational content without replacing administrator edits."""
    seed_questions()

@app.cli.command("make-admin")
@__import__("click").argument("username")
def make_admin(username):
    """Promote an existing account: flask --app app make-admin USERNAME"""
    import click
    user=User.query.filter_by(username=username).first()
    if not user:
        click.echo("Utilisateur introuvable."); return
    user.role="admin"; db.session.commit(); click.echo(f"{username} est maintenant administrateur.")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
