import json
from html import unescape
import os
import tempfile
import time
import unittest
from unittest.mock import patch

_instance_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance")
_fd, _db_path = tempfile.mkstemp(prefix="infoconcours-tests-", suffix=".db", dir=_instance_dir)
os.close(_fd)
_previous_database_url = os.environ.get("DATABASE_URL")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.basename(_db_path)
os.environ.setdefault("SECRET_KEY", "isolated-test-secret-not-for-deployment")

from app import Attempt, CourseExercise, ExerciseAttempt, CurriculumChapter, CurriculumLesson, CurriculumModule, CurriculumSubject, Diagnostic, LessonCompletion, LessonProgress, Question, QuestionMetadata, StudyGoal, StudySession, User, UserPreference, VideoMetadata, VideoResource, VideoWatch, app as global_app, adaptive_level_for_score, adaptive_question_set, build_study_recommendations, calculate_mastery, create_app, db, extract_youtube_video_id, login_manager, seed_questions
from content_quality import LEVELS, audit_lesson
from phase8_lesson_content import PHASE8_DETAILS, CODE_EXAMPLES
from exercise_grading import evaluate_open_answer, short_answer_matches


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        seed_questions()
        self.alice = User(username="alice", email="alice@example.test")
        self.alice.set_password("a-secure-password")
        self.bob = User(username="bob", email="bob@example.test")
        self.bob.set_password("another-secure-password")
        db.session.add_all([self.alice, self.bob])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.app.extensions["sqlalchemy"].engines[None].dispose()
        self.ctx.pop()

    @classmethod
    def tearDownClass(cls):
        with global_app.app_context():
            global_app.extensions["sqlalchemy"].engines[None].dispose()
        try:
            os.remove(_db_path)
        except OSError:
            pass
        if _previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = _previous_database_url

    def login_as(self, user):
        with self.app.test_request_context("/", environ_base=self.client.environ_base):
            session_id = login_manager._session_identifier_generator()
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
            session["_id"] = session_id

    def test_development_startup_generates_ephemeral_key_and_uses_isolated_database(self):
        with patch.dict(os.environ,{"APP_ENV":"development","SECRET_KEY":"","DATABASE_URL":""}):
            local_app=create_app({"AUTO_CREATE_SCHEMA":False})
            self.assertEqual(len(local_app.config["SECRET_KEY"]),64)
            self.assertEqual(local_app.config["SQLALCHEMY_DATABASE_URI"],"sqlite:///infoconcours-phase8-dev.db")
            local_app.extensions["sqlalchemy"].engines[None].dispose()

    def test_non_development_startup_still_requires_explicit_secret(self):
        with patch.dict(os.environ,{"APP_ENV":"production","SECRET_KEY":"","DATABASE_URL":"sqlite:///production-config-test.db"}):
            with self.assertRaisesRegex(RuntimeError,"Set SECRET_KEY"):
                create_app({"AUTO_CREATE_SCHEMA":False})

    def test_private_pages_require_authentication(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)

    def test_registration_validates_email_and_hashes_password(self):
        response = self.client.post("/register", data={"username": "newstudent", "email": "not-an-email", "password": "long-password-123", "confirm": "long-password-123"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(User.query.filter_by(username="newstudent").first())
        response = self.client.post("/register", data={"username": "newstudent", "email": "new@example.test", "password": "long-password-123", "confirm": "long-password-123"})
        self.assertEqual(response.status_code, 302)
        user = User.query.filter_by(username="newstudent").one()
        self.assertNotEqual(user.password_hash, "long-password-123")
        self.assertTrue(user.check_password("long-password-123"))

    def test_profile_password_change_checks_current_password(self):
        self.login_as(self.alice)
        response = self.client.post("/profile", data={"action": "password", "email": self.alice.email, "current_password": "a-secure-password", "new_password": "new-secure-password", "confirm_password": "new-secure-password"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(db.session.get(User, self.alice.id).check_password("new-secure-password"))

    def test_authenticated_learning_pages_render(self):
        self.login_as(self.alice)
        for path in ("/dashboard", "/courses", "/courses/reseaux", "/videos", "/qcm", "/exam", "/planner", "/study", "/errors", "/bookmarks", "/profile"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_user_cannot_read_another_users_diagnostic(self):
        record = Diagnostic(user_id=self.alice.id, scores=json.dumps({}), total=0)
        db.session.add(record)
        db.session.commit()
        self.login_as(self.bob)
        self.assertEqual(self.client.get(f"/diagnostic/{record.id}").status_code, 404)

    def test_login_is_rate_limited_per_ip(self):
        for _ in range(10):
            self.client.post("/login", data={"username": "unknown", "password": "wrong"})
        response = self.client.post("/login", data={"username": "another-name", "password": "wrong"})
        self.assertEqual(response.status_code, 429)

    def test_admin_can_add_and_deactivate_question(self):
        self.alice.role = "admin"
        db.session.commit()
        self.login_as(self.alice)
        chapter=CurriculumChapter.query.join(CurriculumModule).join(CurriculumSubject).filter(CurriculumSubject.name=="Réseaux").order_by(CurriculumChapter.position).first()
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.assertEqual(self.client.get("/admin/curriculum").status_code,200)
        response = self.client.post("/admin", data={"action": "create_question", "domain": "Réseaux", "chapter_id":str(chapter.id), "learning_objective":"Relier la résolution DNS aux noms et adresses IP.", "level": "Facile", "topic": "DNS", "prompt_fr": "Que résout le service DNS ?", "option_0": "Nom de domaine", "option_1": "Adresse IP", "option_2": "Fichier local", "option_3": "Port USB", "answer": "1", "explanation_fr": "DNS associe un nom de domaine à des données, notamment une adresse IP."})
        self.assertEqual(response.status_code, 302)
        q = Question.query.filter_by(topic="DNS").one()
        self.assertFalse(q.active)
        self.assertEqual(QuestionMetadata.query.filter_by(question_id=q.id).one().learning_objective,"Relier la résolution DNS aux noms et adresses IP.")
        response = self.client.post("/admin", data={"action": "toggle_question", "question_id": str(q.id)})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(db.session.get(Question, q.id).active)

    def test_video_management_is_admin_only_and_rejects_unparseable_links(self):
        self.login_as(self.alice)
        self.assertEqual(self.client.get("/admin/videos").status_code, 403)
        self.alice.role = "admin"
        db.session.commit()
        self.assertEqual(self.client.get("/admin/videos").status_code, 200)
        response = self.client.post("/admin/videos", data={"action": "create", "title": "Test", "channel": "Test", "url": "https://example.com/not-youtube", "lesson_key": "reseaux", "language": "Français", "verified": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VideoResource.query.count(), 0)

    def test_question_bank_has_200_distinct_items_distributed_across_eight_subjects(self):
        self.assertEqual(Question.query.count(), 200)
        for name, _, _ in __import__("app").DOMAINS:
            self.assertEqual(Question.query.filter_by(domain=name, active=True).count(), 25)
        prompts=[(q.domain,q.prompt_fr) for q in Question.query.all()]
        self.assertEqual(len(prompts),len(set(prompts)))
        self.assertEqual(QuestionMetadata.query.count(),200)
        for question in Question.query.all():
            options=json.loads(question.options_fr)
            self.assertEqual(len(options),4)
            self.assertEqual(len(set(options)),4)
            self.assertIn(question.answer,range(4))
            self.assertTrue(question.prompt_fr.strip())
            self.assertTrue(question.explanation_fr.strip())
            meta=QuestionMetadata.query.filter_by(question_id=question.id).one()
            self.assertTrue(meta.chapter_id)
            self.assertTrue(meta.lesson_id)
        for level in ("Débutant","Élémentaire","Intermédiaire","Avancé","Expert"):
            self.assertGreater(Question.query.filter_by(level=level,active=True).count(),0)
        for name,_,_ in __import__("app").DOMAINS:
            for level in ("Débutant","Élémentaire","Intermédiaire","Avancé","Expert"):
                self.assertGreater(Question.query.filter_by(domain=name,level=level,active=True).count(),0)

    def test_curriculum_has_complete_required_structure(self):
        from curriculum_data import CURRICULUM
        self.assertEqual(len(CURRICULUM),8)
        self.assertEqual(sum(len(subject["modules"]) for subject in CURRICULUM),16)
        lessons=[]
        for subject in CURRICULUM:
            self.assertEqual(len(subject["modules"]),2)
            for module in subject["modules"]:
                for chapter in module["chapters"]:
                    lessons.append(chapter["lesson"])
        self.assertEqual(len(lessons),32)
        for lesson in lessons:
            for field in ("title","objectives","prerequisites","theory","darija","example","exercise","solution","summary","revision"):
                self.assertTrue(str(lesson.get(field,"")).strip(),msg=f"Missing {field}: {lesson.get('title')}")
        for lesson_row in CurriculumLesson.query.all():
            self.assertGreaterEqual(len(lesson_row.theory_fr),700)
            for section in ("INTRODUCTION","DÉFINITIONS IMPORTANTES","DÉMARCHE PAS À PAS","APPLICATIONS","ERREURS FRÉQUENTES","CONSEIL POUR L’ÉPREUVE"):
                self.assertIn(section,lesson_row.theory_fr,lesson_row.title)
            self.assertGreaterEqual(CourseExercise.query.filter_by(lesson_id=lesson_row.id,published=True).count(),2)
            self.assertGreaterEqual(db.session.query(QuestionMetadata).join(Question,Question.id==QuestionMetadata.question_id).filter(QuestionMetadata.chapter_id==lesson_row.chapter_id,Question.active.is_(True)).count(),3)
        lesson=CurriculumLesson.query.first(); original=lesson.theory_fr; lesson.theory_fr+="\nNote relue par l’administration."; db.session.commit()
        seed_questions()
        self.assertEqual(db.session.get(CurriculumLesson,lesson.id).theory_fr,original+"\nNote relue par l’administration.")
        self.assertEqual((Question.query.count(),CourseExercise.query.count()),(200,224))
        self.assertEqual((CourseExercise.query.count(),CourseExercise.query.filter_by(learning_objective_fr="").count()),(224,64))

    def test_phase7_exercises_are_distinct_associated_at_all_five_levels_and_seed_is_idempotent(self):
        lessons=CurriculumLesson.query.all()
        self.assertEqual(len(lessons),32)
        for lesson in lessons:
            rows=CourseExercise.query.filter_by(lesson_id=lesson.id,published=True).all()
            self.assertTrue(set(LEVELS).issubset({row.level for row in rows}))
            phase7=[row for row in rows if row.level in LEVELS and row.learning_objective_fr]
            self.assertEqual(len(phase7),5)
            self.assertEqual(len({row.prompt_fr for row in phase7}),5)
            self.assertTrue(all(row.exercise_type=="open" for row in phase7))
        before=CourseExercise.query.count(); seed_questions(); self.assertEqual(CourseExercise.query.count(),before)

    def test_content_audit_reports_real_missing_sections_and_never_claims_expert_validation(self):
        lesson=CurriculumLesson.query.first(); chapter=db.session.get(CurriculumChapter,lesson.chapter_id)
        rows=CourseExercise.query.filter_by(lesson_id=lesson.id,published=True).all()
        report=audit_lesson(lesson,chapter,rows,0)
        self.assertFalse(report["complete"])
        self.assertIn("vidéo dédiée vérifiée",report["missing"])
        self.assertIn("théorie détaillée (cible 1 500 mots)",report["missing"])
        self.assertGreaterEqual(report["distinct_example_count"],3)
        self.assertTrue(report["expert_review"])

    def test_phase8_authored_material_covers_all_32_topics_with_examples_and_code(self):
        self.assertEqual(len(PHASE8_DETAILS),32)
        for chapter_title,detail in PHASE8_DETAILS.items():
            chapter=CurriculumChapter.query.filter_by(title=chapter_title).one()
            lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).one()
            self.assertEqual(len(detail["examples"]),3,chapter_title)
            self.assertEqual(audit_lesson(lesson,chapter,CourseExercise.query.filter_by(lesson_id=lesson.id,published=True).all())["distinct_example_count"],3,chapter_title)
            self.assertGreaterEqual(len(json.loads(lesson.objectives_fr)),5,chapter_title)
            self.assertIn("DÉMONSTRATION PAS À PAS",lesson.theory_fr,chapter_title)
            self.assertGreaterEqual(len(lesson.theory_fr.split()),400,chapter_title)
        for chapter_title,code in CODE_EXAMPLES.items():
            if chapter_title not in {"Entités, relations et contraintes","Normalisation et qualité","SQL : filtrer et joindre","Transactions et index"}:
                compile(code,f"{chapter_title}.py","exec")

    def test_phase8_sql_examples_execute_and_match_the_documented_results(self):
        import sqlite3
        from phase8_lesson_content import CODE_EXAMPLES
        for chapter_title in ("Entités, relations et contraintes","Normalisation et qualité","SQL : filtrer et joindre","Transactions et index"):
            with self.subTest(chapter=chapter_title):
                conn=sqlite3.connect(":memory:")
                conn.executescript(CODE_EXAMPLES[chapter_title])
                if chapter_title=="SQL : filtrer et joindre":
                    self.assertEqual(conn.execute("SELECT titre, COUNT(*) FROM Cours JOIN Inscription ON Inscription.cours_id=Cours.id GROUP BY Cours.id").fetchone(),("Réseaux",3))
                if chapter_title=="Transactions et index":
                    self.assertEqual(conn.execute("SELECT id,solde FROM Compte ORDER BY id").fetchall(),[(1,400),(2,300)])
                conn.close()

    def test_youtube_url_parser_requires_a_real_https_youtube_host_and_valid_id(self):
        self.assertEqual(extract_youtube_video_id("https://www.youtube.com/watch?v=M7lc1UVf-VE"),"M7lc1UVf-VE")
        self.assertEqual(extract_youtube_video_id("https://youtu.be/M7lc1UVf-VE"),"M7lc1UVf-VE")
        self.assertEqual(extract_youtube_video_id("https://youtube.com/shorts/M7lc1UVf-VE"),"M7lc1UVf-VE")
        for url in ("http://youtube.com/watch?v=M7lc1UVf-VE","https://youtube.com.evil.test/watch?v=M7lc1UVf-VE","https://youtube.com@evil.test/watch?v=M7lc1UVf-VE","https://youtu.be/not-an-id"):
            self.assertIsNone(extract_youtube_video_id(url),url)

    def test_admin_can_create_edit_and_publish_lesson_and_non_admin_is_denied(self):
        self.login_as(self.alice)
        self.assertEqual(self.client.get("/admin/curriculum").status_code,403)
        self.alice.role="admin"; db.session.commit()
        self.assertEqual(self.client.get("/admin/curriculum").status_code,200)
        chapter=CurriculumChapter.query.first()
        response=self.client.post("/admin/curriculum",data={"action":"create_lesson","chapter_id":chapter.id,"title":"Test lesson","objectives_fr":"Objectif 1\nObjectif 2","prerequisites_fr":"Variables","theory_fr":"Explication test détaillée.","theory_ar":"شرح تجريبي بالدارجة.","example_fr":"Exemple de test.","code_example":"x = 1","exercise_fr":"Calculer x + 1.","solution_fr":"La réponse est 2.","summary_fr":"Résumé de test.","revision_fr":"Relire la définition."})
        self.assertEqual(response.status_code,302)
        lesson=CurriculumLesson.query.filter_by(title="Test lesson").one()
        self.assertFalse(lesson.published)
        response=self.client.post("/admin/curriculum",data={"action":"toggle_lesson","id":lesson.id})
        self.assertEqual(response.status_code,302)
        self.assertTrue(db.session.get(CurriculumLesson,lesson.id).published)
        response=self.client.post("/admin/curriculum",data={"action":"edit_lesson","id":lesson.id,"title":"Edited lesson","objectives_fr":"Revised objective","prerequisites_fr":"Variables","theory_fr":"Updated French explanation.","theory_ar":"شرح محدث بالدارجة.","example_fr":"Updated example.","code_example":"","exercise_fr":"Updated exercise.","solution_fr":"Updated solution.","summary_fr":"Updated summary.","revision_fr":"Updated revision."})
        self.assertEqual(response.status_code,302)
        self.assertEqual(db.session.get(CurriculumLesson,lesson.id).title,"Edited lesson")
        module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        response=self.client.post("/admin/curriculum",data={"action":"toggle_lesson","id":lesson.id})
        self.assertEqual(response.status_code,302)
        response=self.client.get(f"/courses/{subject.slug}/lesson/{lesson.id}")
        self.assertEqual(response.status_code,404)

    def test_admin_can_add_a_custom_academy_subject_and_category(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        response=self.client.post("/admin/curriculum",data={"action":"create_subject","name":"Culture numérique","slug":"culture-numerique","category":"Compléments","weight":"5"})
        self.assertEqual(response.status_code,302)
        subject=CurriculumSubject.query.filter_by(slug="culture-numerique").one()
        self.assertEqual((subject.category,subject.weight),("Compléments",5))
        self.assertEqual(self.client.get("/courses/culture-numerique").status_code,200)
        self.assertEqual(self.client.get("/qcm?domain=Culture%20num%C3%A9rique").status_code,200)

    def test_admin_can_create_question_with_chapter_and_optional_time_limit(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        chapter=CurriculumChapter.query.first()
        module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        data={"action":"create_question","domain":subject.name,"level":"Expert","topic":chapter.title,"learning_objective":"Vérifier la validité des données avant le traitement.","prompt_fr":"Quelle vérification pédagogique est-elle attendue ?","prompt_ar":"","option_0":"Vérifier les entrées","option_1":"Ignorer les entrées","option_2":"Supprimer le résultat","option_3":"Remplacer le type","answer":"0","explanation_fr":"Valider l’entrée évite de traiter des données hors du domaine prévu.","chapter_id":str(chapter.id),"time_limit_seconds":"45"}
        response=self.client.post("/admin",data=data)
        self.assertEqual(response.status_code,302)
        q=Question.query.filter_by(prompt_fr=data["prompt_fr"]).one()
        self.assertEqual(q.level,"Expert")
        meta=QuestionMetadata.query.filter_by(question_id=q.id).one()
        self.assertEqual((meta.chapter_id,meta.time_limit_seconds),(chapter.id,45))
        data.update(action="edit_question",question_id=str(q.id),prompt_fr="Question éditée ?",explanation_fr="Correction éditée.")
        response=self.client.post("/admin",data=data)
        self.assertEqual(response.status_code,302)
        self.assertEqual(db.session.get(Question,q.id).prompt_fr,"Question éditée ?")

    def test_diagnostic_counts_only_answered_questions(self):
        self.login_as(self.alice)
        q = Question.query.filter_by(domain="Algorithmique", active=True).first()
        response = self.client.post("/diagnostic", data={f"q{q.id}": str(q.answer)})
        self.assertEqual(response.status_code, 302)
        record = Diagnostic.query.filter_by(user_id=self.alice.id).one()
        score = json.loads(record.scores)["Algorithmique"]
        self.assertEqual(score["count"], 1)
        self.assertEqual(score["correct"], 1)
        result=self.client.get(response.location)
        self.assertEqual(result.status_code,200)
        self.assertIn("Non évaluée",result.get_data(as_text=True))

    def test_initial_diagnostic_balances_three_questions_across_all_eight_subjects(self):
        self.login_as(self.alice)
        response=self.client.get("/diagnostic")
        self.assertEqual(response.status_code,200)
        with self.client.session_transaction() as session:
            ids=session["active_diagnostic_ids"]
        qs=[db.session.get(Question,qid) for qid in ids]
        self.assertEqual(len(qs),24)
        self.assertEqual({q.domain for q in qs},{domain for domain,_,_ in __import__("app").DOMAINS})
        for domain,_,_ in __import__("app").DOMAINS:
            self.assertEqual(sum(q.domain==domain for q in qs),3)

    def test_adaptive_score_bands_and_custom_thresholds(self):
        self.assertEqual(adaptive_level_for_score(30),"Débutant")
        self.assertEqual(adaptive_level_for_score(80),"Avancé")
        self.assertEqual(adaptive_level_for_score(95),"Expert / défi")
        self.assertEqual(adaptive_level_for_score(70,[35,55,70,88]),"Avancé")
        self.assertIsNone(adaptive_level_for_score(None))

    def test_adaptive_question_selector_uses_per_subject_performance_and_actual_levels(self):
        initial,_=adaptive_question_set(self.alice.id,domain="Algorithmique",limit=5)
        self.assertTrue(all(q.level in {"Facile","Moyen","Débutant","Élémentaire","Intermédiaire"} for q in initial))
        questions=Question.query.filter_by(domain="Algorithmique",active=True).order_by(Question.id).limit(5).all()
        details=[{"question_id":q.id,"domain":"Algorithmique","topic":q.topic,"level":q.level,"ok":i<4} for i,q in enumerate(questions)]
        attempt=Attempt(user_id=self.alice.id,mode="qcm",score=sum(item["ok"] for item in details),total=len(details),details=json.dumps(details))
        db.session.add(attempt); db.session.commit()
        selected,reason=adaptive_question_set(self.alice.id,domain="Algorithmique",limit=5)
        self.assertEqual(adaptive_level_for_score(calculate_mastery(self.alice.id)["Algorithmique"]["percent"]),"Avancé")
        self.assertTrue(any(q.level in {"Moyen","Difficile"} for q in selected))
        self.assertIn("réponses évaluées",reason)

    def test_adaptive_question_selection_respects_30_80_95_percent_in_all_subjects(self):
        from app import ADAPTIVE_QUESTION_LEVELS
        scenarios=((30,"Débutant"),(80,"Avancé"),(95,"Expert / défi"))
        domains=[row[0] for row in __import__("app").DOMAINS]
        for score,stage in scenarios:
            student=User(username=f"stage{score}",email=f"stage{score}@example.test")
            student.set_password("a-secure-password")
            db.session.add(student); db.session.flush()
            evidence={domain:{"percent":score,"count":10} for domain in domains}
            db.session.add(Diagnostic(user_id=student.id,scores=json.dumps(evidence),total=80)); db.session.commit()
            for domain in domains:
                selected,_=adaptive_question_set(student.id,domain=domain,limit=5)
                self.assertTrue(selected, f"no {stage} questions for {domain}")
                self.assertTrue(all(q.level in ADAPTIVE_QUESTION_LEVELS[stage] for q in selected),f"wrong level for {score}% in {domain}")

    def test_mastery_is_empty_without_assessment_evidence(self):
        score = calculate_mastery(self.alice.id)["Réseaux"]
        self.assertIsNone(score["percent"])
        self.assertEqual(score["confidence"], "Insuffisante")

    def test_mastery_hides_percentages_until_three_answers_are_recorded(self):
        attempt=Attempt(user_id=self.alice.id,mode="qcm",score=1,total=2,details=json.dumps([{"domain":"Réseaux","topic":"OSI","ok":True},{"domain":"Réseaux","topic":"OSI","ok":False}]))
        db.session.add(attempt); db.session.commit()
        score=calculate_mastery(self.alice.id)["Réseaux"]
        self.assertIsNone(score["percent"])
        self.assertEqual(score["count"],2)
        self.assertEqual(score["topics"],[])

    def test_qcm_persists_validated_answer_and_mastery(self):
        self.login_as(self.alice)
        self.client.get("/qcm?domain=R%C3%A9seaux")
        with self.client.session_transaction() as session:
            ids = session["active_qcm_ids"]
        qs = [db.session.get(Question, qid) for qid in ids]
        data = {"qid": [str(q.id) for q in qs], **{f"a{q.id}": str(q.answer) for q in qs}}
        response = self.client.post("/qcm", data=data)
        self.assertEqual(response.status_code, 200)
        attempt = Attempt.query.filter_by(user_id=self.alice.id, mode="qcm").one()
        self.assertEqual(attempt.score, len(qs))
        self.assertEqual(calculate_mastery(self.alice.id)["Réseaux"]["percent"], 100)
        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)

    def test_qcm_wrong_answer_has_corrected_answer_and_explanation(self):
        self.login_as(self.alice)
        self.client.get("/qcm?domain=Algorithmique")
        with self.client.session_transaction() as session:
            ids = session["active_qcm_ids"]
        qs = [db.session.get(Question, qid) for qid in ids]
        data = {"qid": [str(q.id) for q in qs], **{f"a{q.id}": str((q.answer + 1) % 4) for q in qs}}
        q = qs[0]
        response = self.client.post("/qcm", data=data)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn(q.explanation_fr, html)
        self.assertIn(json.loads(q.options_fr)[q.answer], unescape(html))

    def test_study_session_is_saved_to_authenticated_user(self):
        self.login_as(self.alice)
        response = self.client.post("/study", data={"domain": "Réseaux", "minutes": "45"})
        self.assertEqual(response.status_code, 302)
        saved = StudySession.query.filter_by(user_id=self.alice.id).one()
        self.assertEqual((saved.domain, saved.minutes), ("Réseaux", 45))
        self.assertEqual(self.client.get("/study").status_code,200)

    def test_daily_study_goal_is_saved_per_user(self):
        self.login_as(self.alice)
        response = self.client.post("/study", data={"action": "goal", "daily_goal": "75"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StudyGoal.query.filter_by(user_id=self.alice.id).one().daily_minutes, 75)
        self.assertIsNone(StudyGoal.query.filter_by(user_id=self.bob.id).first())

    def test_adaptive_plan_uses_actual_weakest_assessment_and_stays_empty_without_evidence(self):
        self.assertEqual(build_study_recommendations(self.alice.id), ([], False))
        details=[{"question_id": index, "domain": "Algorithmique", "topic": "Complexité", "ok": False} for index in range(1,4)]
        attempt = Attempt(user_id=self.alice.id, mode="qcm", score=0, total=3,details=json.dumps(details))
        db.session.add(attempt); db.session.commit()
        plan, personalized = build_study_recommendations(self.alice.id)
        self.assertTrue(personalized)
        self.assertEqual(plan[0]["subject"], "Algorithmique")
        self.assertEqual(plan[0]["topic"], "Complexité")
        self.assertEqual(plan[0]["topic_percent"], 0)

    def test_lesson_requires_scored_evidence_for_validation(self):
        self.login_as(self.alice)
        chapter=CurriculumChapter.query.join(CurriculumModule).join(CurriculumSubject).filter(CurriculumSubject.name=="Réseaux").order_by(CurriculumChapter.id).first()
        qs = Question.query.join(QuestionMetadata).filter(QuestionMetadata.chapter_id==chapter.id,Question.domain=="Réseaux",Question.active.is_(True)).all()
        data = {f"a{q.id}": str(q.answer) for q in qs}
        lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id,published=True).first()
        response = self.client.post(f"/courses/reseaux/lesson/{lesson.id}", data=data)
        self.assertEqual(response.status_code, 302)
        progress = LessonProgress.query.filter_by(user_id=self.alice.id, lesson_key=f"lesson:{lesson.id}").one()
        self.assertEqual(progress.evidence_count, len(qs))

    def test_language_selection_is_persisted_per_user(self):
        self.login_as(self.alice)
        response=self.client.post("/language",data={"language":"ar"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(UserPreference.query.filter_by(user_id=self.alice.id).one().language,"ar")
        self.assertEqual(self.client.get("/dashboard").status_code,200)
        with self.client.session_transaction() as session:
            self.assertEqual(session["language"],"ar")

    def test_main_pages_render_with_french_default_and_selected_darija_locale(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        paths=["/dashboard","/courses","/courses/algorithmique","/qcm","/diagnostic","/planner","/study","/profile","/videos","/exam","/errors","/bookmarks","/admin","/admin/curriculum","/admin/videos","/admin/exercise-attempts"]
        for path in paths:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200,path)
            self.assertIn('<html lang="fr">',response.get_data(as_text=True),path)
        self.client.post("/language",data={"language":"ar"})
        for path in paths:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200,path)
            self.assertIn('<html lang="ar">',response.get_data(as_text=True),path)
        self.client.post("/logout")
        self.client.post("/login",data={"username":"alice","password":"a-secure-password"})
        with self.client.session_transaction() as session:
            self.assertEqual(session["language"],"ar")

    def test_qcm_exercise_is_auto_graded_and_contributes_only_its_real_scores_to_mastery(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        lesson=CurriculumLesson.query.first()
        response=self.client.post("/admin/curriculum",data={"action":"create_exercise","lesson_id":lesson.id,"title":"Typed QCM","exercise_type":"qcm","prompt_fr":"Quel résultat est correct ?","option_0":"A","option_1":"B","option_2":"C","option_3":"D","correct_answer":"1","solution_fr":"B est correct.","level":"Facile"})
        self.assertEqual(response.status_code,302)
        exercise=CourseExercise.query.filter_by(title="Typed QCM").one()
        self.assertEqual(exercise.exercise_type,"qcm")
        self.client.post("/admin/curriculum",data={"action":"toggle_exercise","id":exercise.id})
        for answer,expected in [("1",100),("0",0),("1",100)]:
            response=self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":answer})
            self.assertEqual(response.status_code,302)
            attempt=ExerciseAttempt.query.filter_by(exercise_id=exercise.id).order_by(ExerciseAttempt.id.desc()).first()
            self.assertEqual((attempt.status,attempt.score),("auto_graded",expected))
            self.assertEqual(attempt.feedback,"B est correct.")
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id)
        module=db.session.get(CurriculumModule,chapter.module_id)
        subject=db.session.get(CurriculumSubject,module.subject_id)
        mastery=calculate_mastery(self.alice.id)[subject.name]
        self.assertEqual(mastery["count"],3)
        self.assertIsNotNone(mastery["percent"])
        self.assertIn("Quel résultat",self.client.get(f"/courses/{subject.slug}/lesson/{lesson.id}").get_data(as_text=True))

    def test_true_false_and_short_answer_exercises_are_objectively_graded(self):
        self.login_as(self.alice)
        lesson=CurriculumLesson.query.first()
        truefalse=CourseExercise(lesson_id=lesson.id,title="TF",prompt_fr="La RAM est volatile ?",solution_fr="Oui.",exercise_type="true_false",correct_answer="true",published=True)
        short=CourseExercise(lesson_id=lesson.id,title="Short",prompt_fr="Combien font deux et deux ?",solution_fr="Quatre.",exercise_type="short_answer",correct_answer=None,accepted_answers_json=json.dumps(["4","quatre"]),published=True)
        db.session.add_all([truefalse,short]); db.session.commit()
        self.client.post(f"/exercise/{truefalse.id}/attempt",data={"answer":"true"})
        self.client.post(f"/exercise/{short.id}/attempt",data={"answer":"  QUATRE.  "})
        self.assertEqual(ExerciseAttempt.query.filter_by(exercise_id=truefalse.id).one().score,100)
        self.assertEqual(ExerciseAttempt.query.filter_by(exercise_id=short.id).one().score,100)
        self.client.post(f"/exercise/{truefalse.id}/attempt",data={"answer":"false"})
        wrong_tf=ExerciseAttempt.query.filter_by(exercise_id=truefalse.id).order_by(ExerciseAttempt.id.desc()).first()
        self.assertEqual((wrong_tf.status,wrong_tf.score),("auto_graded",0.0))

    def test_empty_and_oversized_exercise_answers_are_rejected_without_attempts(self):
        self.login_as(self.alice)
        lesson=CurriculumLesson.query.first()
        exercise=CourseExercise(lesson_id=lesson.id,title="Input bounds",prompt_fr="Réponds.",solution_fr="Solution.",exercise_type="open",published=True)
        db.session.add(exercise); db.session.commit()
        for answer in ("   ","x"*12001):
            response=self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":answer})
            self.assertEqual(response.status_code,302)
        self.assertEqual(ExerciseAttempt.query.filter_by(exercise_id=exercise.id).count(),0)

    def test_short_answers_accept_case_punctuation_synonyms_and_equivalent_decimals(self):
        self.assertTrue(short_answer_matches("  QUATRE ! ",["4", "quatre"]))
        self.assertTrue(short_answer_matches("3,50",["3.5"]))
        self.assertTrue(short_answer_matches("Réseau local.",["réseau local"]))
        self.assertFalse(short_answer_matches("14",["4"]))

    def test_open_answer_ai_result_is_saved_rendered_and_counted_in_mastery(self):
        self.login_as(self.alice)
        lesson=CurriculumLesson.query.first()
        exercise=CourseExercise(lesson_id=lesson.id,title="Open semantic",prompt_fr="Explique le rôle de la RAM.",solution_fr="La RAM stocke temporairement les données utilisées.",exercise_type="open",learning_objective_fr="Distinguer mémoire volatile",grading_guide_fr="Exactitude et idée de volatilité.",published=True)
        db.session.add(exercise); db.session.commit()
        result={"score":70,"classification":"partially_correct","explanation_fr":"Tu as bien expliqué l’usage temporaire; il manque la volatilité.","missing_concepts":["La RAM est volatile"],"expected_answer_fr":"La RAM conserve temporairement les données des programmes en cours et perd son contenu hors tension.","confidence":0.92}
        self.app.config["EXERCISE_GRADING_EVALUATOR"]=lambda ex,answer: result
        response=self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":"Elle garde ce qui est utilisé maintenant."})
        self.assertEqual(response.status_code,302)
        self.assertTrue(response.location.endswith(f"#exercise-{exercise.id}"))
        attempt=ExerciseAttempt.query.filter_by(exercise_id=exercise.id).one()
        self.assertEqual((attempt.status,attempt.score),("ai_graded",70.0))
        page=self.client.get(response.location.split("#")[0]).get_data(as_text=True)
        self.assertIn("Réponse partiellement correcte",page)
        self.assertIn("La RAM est volatile",page)
        self.assertIn("Elle garde ce qui est utilisé maintenant.",page)
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id); module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        self.assertIsNone(calculate_mastery(self.alice.id)[subject.name]["percent"])
        self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":"Elle garde ce qui est utilisé maintenant."})
        self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":"Elle garde ce qui est utilisé maintenant."})
        self.assertEqual(calculate_mastery(self.alice.id)[subject.name]["percent"],70.0)
        self.assertEqual(self.client.get(response.location.split("#")[0]).status_code,200)
        self.app.config.pop("EXERCISE_GRADING_EVALUATOR",None)

    def test_open_ai_low_confidence_invalid_result_and_provider_failure_stay_manual(self):
        self.login_as(self.alice)
        lesson=CurriculumLesson.query.first()
        exercise=CourseExercise(lesson_id=lesson.id,title="Open cautious",prompt_fr="Explique.",solution_fr="Réponse.",exercise_type="open",published=True)
        db.session.add(exercise); db.session.commit()
        base={"score":0,"classification":"incorrect","explanation_fr":"À revoir.","missing_concepts":[],"expected_answer_fr":"Réponse.","confidence":0.40}
        evaluators=[lambda ex,answer:base,lambda ex,answer:{"score":900},lambda ex,answer:(_ for _ in ()).throw(RuntimeError("provider_unavailable"))]
        for index,evaluator in enumerate(evaluators):
            self.app.config["EXERCISE_GRADING_EVALUATOR"]=evaluator
            response=self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":f"Essai {index}"})
            self.assertEqual(response.status_code,302)
        rows=ExerciseAttempt.query.filter_by(exercise_id=exercise.id).order_by(ExerciseAttempt.id).all()
        self.assertEqual([row.status for row in rows],["pending_manual"]*3)
        self.assertTrue(all(row.score is None for row in rows))
        self.assertEqual(ExerciseAttempt.query.filter_by(exercise_id=exercise.id).count(),3)
        confident_incorrect={"score":0,"classification":"incorrect","explanation_fr":"La réponse confond les notions.","missing_concepts":["La définition attendue"],"expected_answer_fr":"Réponse.","confidence":0.94}
        self.app.config["EXERCISE_GRADING_EVALUATOR"]=lambda ex,answer:confident_incorrect
        self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":"Réponse contraire."})
        wrong=ExerciseAttempt.query.filter_by(exercise_id=exercise.id).order_by(ExerciseAttempt.id.desc()).first()
        self.assertEqual((wrong.status,wrong.score),("ai_graded",0.0))
        self.assertIn("Réponse incorrecte",wrong.feedback)
        self.app.config.pop("EXERCISE_GRADING_EVALUATOR",None)

    def test_open_ai_responses_request_includes_rubric_objective_and_answer_and_validates_output(self):
        lesson=CurriculumLesson.query.first()
        exercise=CourseExercise(lesson_id=lesson.id,title="Rubric payload",prompt_fr="Question.",solution_fr="Réponse attendue.",exercise_type="open",grading_guide_fr="Méthode correcte.",learning_objective_fr="Expliquer le concept.")
        valid={"score":90,"classification":"correct","explanation_fr":"Bonne réponse.","missing_concepts":[],"expected_answer_fr":"Réponse attendue.","confidence":0.9}
        payload={"output":[{"type":"message","content":[{"type":"output_text","text":json.dumps(valid,ensure_ascii=False)}]}]}
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,limit): return json.dumps(payload,ensure_ascii=False).encode("utf-8")
        with patch.dict(os.environ,{"EXERCISE_GRADING_PROVIDER":"openai","OPENAI_API_KEY":"unit-test-only","EXERCISE_GRADING_MODEL":"test-model"}):
            with patch("exercise_grading.urlopen",return_value=FakeResponse()) as mocked:
                result=evaluate_open_answer(exercise,"Ma réponse reformulée.")
        self.assertEqual((result["score"],result["classification"]),(90.0,"correct"))
        request=mocked.call_args.args[0]
        sent=json.loads(request.data); content=json.loads(sent["input"])
        self.assertEqual({"title","question","expected_solution","rubric","learning_objective","student_answer"},set(content))
        self.assertEqual(content["student_answer"],"Ma réponse reformulée.")

    def test_open_exercise_waits_for_manual_feedback_without_mastery_score(self):
        self.login_as(self.alice)
        lesson=CurriculumLesson.query.first()
        exercise=CourseExercise(lesson_id=lesson.id,title="Open",prompt_fr="Explique.",solution_fr="Référence.",exercise_type="open",grading_guide_fr="Clarté, exactitude.",published=True)
        db.session.add(exercise); db.session.commit()
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id); module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        self.client.post(f"/exercise/{exercise.id}/attempt",data={"answer":"Réponse rédigée."})
        attempt=ExerciseAttempt.query.filter_by(exercise_id=exercise.id).one()
        self.assertEqual(attempt.status,"pending_manual")
        self.assertIsNone(attempt.score)
        self.assertIsNone(calculate_mastery(self.alice.id)[subject.name]["percent"])
        self.assertEqual(self.client.get("/admin/exercise-attempts").status_code,403)
        self.alice.role="admin"; db.session.commit()
        self.assertEqual(self.client.get("/admin/exercise-attempts").status_code,200)
        response=self.client.post("/admin/exercise-attempts",data={"attempt_id":attempt.id,"score":"82","feedback":"Bonne analyse; précise la définition."})
        self.assertEqual(response.status_code,302)
        db.session.refresh(attempt)
        self.assertEqual((attempt.status,attempt.score,attempt.feedback),("manually_graded",82.0,"Bonne analyse; précise la définition."))
        self.assertIsNone(calculate_mastery(self.alice.id)[subject.name]["percent"])

    def test_learner_can_continue_and_mark_lesson_complete(self):
        self.login_as(self.alice)
        response=self.client.get("/courses/continue")
        self.assertEqual(response.status_code,302)
        lesson=CurriculumLesson.query.filter_by(published=True).order_by(CurriculumLesson.id).first()
        chapter=db.session.get(CurriculumChapter,lesson.chapter_id); module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        self.assertIn(f"/courses/{subject.slug}/lesson/{lesson.id}",response.location)
        self.client.get(response.location)
        progress=LessonProgress.query.filter_by(user_id=self.alice.id,lesson_key=f"lesson:{lesson.id}").one()
        self.assertEqual(progress.evidence_count,0)
        response=self.client.post(f"/courses/{subject.slug}/lesson/{lesson.id}/complete")
        self.assertEqual(response.status_code,302)
        self.assertEqual(LessonCompletion.query.filter_by(user_id=self.alice.id,lesson_id=lesson.id).count(),1)
        page=self.client.get(f"/courses/{subject.slug}/lesson/{lesson.id}").get_data(as_text=True)
        self.assertIn("Leçon terminée",page)
        self.assertEqual(self.client.get("/courses").status_code,200)

    def test_admin_can_create_video_metadata_and_reject_unsafe_thumbnail(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        chapter=CurriculumChapter.query.first()
        module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first()
        response=self.client.post("/admin/videos",data={"action":"create","title":"YouTube IFrame Player API demo","channel":"YouTube Developers","url":"https://www.youtube.com/watch?v=M7lc1UVf-VE","lesson_key":subject.slug,"lesson_id":str(lesson.id),"chapter_id":str(chapter.id),"language":"Français","description":"Official player API sample used only in this isolated test.","thumbnail_url":"https://img.youtube.com/vi/M7lc1UVf-VE/hqdefault.jpg","duration_minutes":"5","verified":"yes"})
        self.assertEqual(response.status_code,302)
        video=VideoResource.query.filter_by(video_id="M7lc1UVf-VE").one()
        self.assertTrue(video.verified)
        self.assertEqual(video.duration_minutes,5)
        from app import VideoMetadata
        metadata=VideoMetadata.query.filter_by(video_id=video.id).one()
        self.assertEqual(metadata.chapter_id,chapter.id)
        self.assertEqual(metadata.lesson_id,lesson.id)
        self.assertIn("Official player",metadata.description)
        self.client.post(f"/videos/{video.id}/watched")
        response=self.client.post("/admin/videos",data={"action":"edit","video_id":str(video.id),"title":"Edited player demo","channel":"YouTube Developers","url":"https://youtu.be/M7lc1UVf-VE","lesson_key":subject.slug,"chapter_id":str(chapter.id),"language":"Français","description":"Updated description.","thumbnail_url":"https://img.youtube.com/vi/M7lc1UVf-VE/hqdefault.jpg","duration_minutes":"5"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(db.session.get(VideoResource,video.id).title,"Edited player demo")
        self.assertEqual(db.session.get(VideoResource,video.id).video_id,"M7lc1UVf-VE")
        self.assertEqual(db.session.get(VideoResource,video.id).verification_status,"pending")
        self.assertFalse(db.session.get(VideoResource,video.id).verified)
        response=self.client.post("/admin/videos",data={"action":"edit","video_id":str(video.id),"title":"Unsafe thumbnail","channel":"YouTube Developers","url":"https://www.youtube.com/watch?v=M7lc1UVf-VE","lesson_key":subject.slug,"chapter_id":str(chapter.id),"language":"Français","description":"Updated description.","thumbnail_url":"javascript:alert(1)","duration_minutes":"5"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(db.session.get(VideoResource,video.id).title,"Edited player demo")
        self.assertEqual(self.client.get("/videos").status_code,200)

    def test_video_review_workflow_starts_pending_and_admin_can_reject_or_approve(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        chapter=CurriculumChapter.query.first(); module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id).first()
        data={"action":"create","title":"Review candidate","channel":"Test channel","url":"https://www.youtube.com/watch?v=M7lc1UVf-VE","lesson_key":subject.slug,"lesson_id":str(lesson.id),"language":"Français"}
        self.client.post("/admin/videos",data=data)
        video=VideoResource.query.one()
        self.assertEqual((video.verification_status,video.verified),("pending",False))
        self.assertEqual(self.client.get("/videos").status_code,200)
        self.client.post("/admin/videos",data={"action":"reject","video_id":str(video.id)})
        self.assertEqual(db.session.get(VideoResource,video.id).verification_status,"rejected")
        self.client.post("/admin/videos",data={"action":"verify","video_id":str(video.id)})
        video=db.session.get(VideoResource,video.id)
        self.assertEqual(video.verification_status,"verified"); self.assertTrue(video.verified); self.assertIsNotNone(video.verified_at)

    def test_admin_quality_page_has_subject_chapter_and_status_filters(self):
        self.login_as(self.alice)
        self.assertEqual(self.client.get("/admin/quality").status_code,403)
        self.alice.role="admin"; db.session.commit()
        self.login_as(self.alice)
        chapter=CurriculumChapter.query.first(); subject=db.session.get(CurriculumSubject,db.session.get(CurriculumModule,chapter.module_id).subject_id)
        response=self.client.get(f"/admin/quality?subject={subject.id}&chapter={chapter.id}&status=incomplete")
        self.assertEqual(response.status_code,200)
        self.assertIn(b"Audit mesurable",response.data)

    def test_admin_can_create_edit_and_publish_an_exercise(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        lesson=CurriculumLesson.query.first()
        response=self.client.post("/admin/curriculum",data={"action":"create_exercise","lesson_id":str(lesson.id),"title":"Practice","prompt_fr":"Trace the algorithm.","solution_fr":"The loop runs three times.","level":"Facile"})
        self.assertEqual(response.status_code,302)
        exercise=CourseExercise.query.filter_by(title="Practice").one()
        self.assertFalse(exercise.published)
        response=self.client.post("/admin/curriculum",data={"action":"edit_exercise","id":str(exercise.id),"title":"Practice updated","prompt_fr":"Trace the revised algorithm.","solution_fr":"The loop runs four times.","level":"Moyen"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(db.session.get(CourseExercise,exercise.id).level,"Moyen")
        response=self.client.post("/admin/curriculum",data={"action":"toggle_exercise","id":str(exercise.id)})
        self.assertEqual(response.status_code,302)
        self.assertTrue(db.session.get(CourseExercise,exercise.id).published)

    def test_video_completion_is_saved_per_user(self):
        self.alice.role="admin"; db.session.commit(); self.login_as(self.alice)
        resource=VideoResource(title="YouTube IFrame Player API demo",channel="YouTube Developers",video_id="M7lc1UVf-VE",language="Français",lesson_key="reseaux",verified=True,verification_status="verified",active=True,created_by=self.alice.id)
        db.session.add(resource); db.session.commit()
        self.client.post(f"/videos/{resource.id}/watched")
        self.assertEqual(VideoWatch.query.filter_by(user_id=self.alice.id,video_id=resource.id).count(),1)

    def test_verified_chapter_video_is_embedded_in_lesson_and_can_return_there(self):
        self.login_as(self.alice)
        chapter=CurriculumChapter.query.filter_by(published=True).order_by(CurriculumChapter.id).first()
        module=db.session.get(CurriculumModule,chapter.module_id); subject=db.session.get(CurriculumSubject,module.subject_id)
        lesson=CurriculumLesson.query.filter_by(chapter_id=chapter.id,published=True).first()
        resource=VideoResource(title="Resource fixture",channel="Channel fixture",video_id="M7lc1UVf-VE",language="Français",lesson_key=subject.name,verified=True,verification_status="verified",active=True,created_by=self.alice.id)
        db.session.add(resource); db.session.flush(); db.session.add(VideoMetadata(video_id=resource.id,description="Fixture description",chapter_id=chapter.id)); db.session.commit()
        response=self.client.get(f"/courses/{subject.slug}/lesson/{lesson.id}")
        self.assertEqual(response.status_code,200)
        self.assertIn("youtube-nocookie.com/embed/M7lc1UVf-VE",response.get_data(as_text=True))
        response=self.client.post(f"/videos/{resource.id}/watched",data={"next":f"/courses/{subject.slug}/lesson/{lesson.id}"})
        self.assertEqual(response.location,f"/courses/{subject.slug}/lesson/{lesson.id}")
        self.login_as(self.bob)
        self.assertEqual(VideoWatch.query.filter_by(user_id=self.bob.id,video_id=resource.id).count(),0)

    def test_exam_ignores_answers_submitted_after_server_deadline(self):
        self.login_as(self.alice)
        self.client.get("/exam")
        with self.client.session_transaction() as session:
            ids = session["active_exam_ids"]
            run_id = session["active_exam_run"]
            session["active_exam_started"] = int(time.time()) - 4 * 60 * 60 - 10
        data = {"qid": [str(qid) for qid in ids], "elapsed": "0", "run_id": run_id}
        for qid in ids:
            data[f"a{qid}"] = str(db.session.get(Question, qid).answer)
        response = self.client.post("/exam", data=data)
        self.assertEqual(response.status_code, 200)
        attempt = Attempt.query.filter_by(user_id=self.alice.id, mode="exam").one()
        self.assertEqual(attempt.score, 0)


if __name__ == "__main__":
    unittest.main()
