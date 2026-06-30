"""caiq_app.py
CAIQ — Career Alignment and Insight Qualifier (Streamlit app).
Run:
  streamlit run app.py
"""
from pathlib import Path
import os
import importlib.util
import json
import hashlib
import io
from contextlib import nullcontext
import html
import math
import re
import zipfile
from html import escape
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go


ETL_DIR = Path(os.getenv("CAIQ_ETL_DIR", Path(__file__).resolve().parent))
MAX_VISIBLE_JOB_AGE_DAYS = int(os.getenv("CAIQ_VISIBLE_JOB_MAX_DAYS", "60"))
I18N = {
    "es": {
        "hero_kicker": "Career Navigator",
        "hero_title": "Define tu próximo paso en Data, IA y Analytics",
        "hero_subtitle": "Descubre qué rol encaja contigo y qué habilidades necesitas para avanzar en el mundo de los datos.",
        "hero_cta_primary": "Analizar perfil",
        "hero_cta_secondary": "Cómo funciona",
        "hero_chip_cv": "Matching con tu CV",
        "hero_chip_gap": "Skill Gap Analysis",
        "hero_chip_masters": "Recomendaciones de Másteres",
        "hero_chip_jobs": "Empleo y Cursos",
        "hero_chip_roadmap": "Roadmap Profesional",
        "profile": "Perfil",
        "target_role": "Rol objetivo",
        "filters": "Filtros",
        "enable_price": "Activar filtro de precio",
        "price_range": "Rango de precio (EUR)",
        "price_range_comparable": "Rango de precio comparable (EUR, coste total)",
        "price_filtering": "Filtrando por precio: {min} - {max}",
        "include_no_price": "Incluir programas sin precio",
        "price_scope_note": "El filtro usa solo precios comparables (coste total del programa).",
        "country": "País",
        "all_countries": "Todos",
        "city": "Localidad / Ciudad",
        "all_cities": "Todas",
        "quick_keyword": "Keyword rápida",
        "none": "Ninguna",
        "any_option": "Todos",
        "manual_keyword": "Keyword manual",
        "manual_placeholder": "Ej: NLP, Deep Learning...",
        "advanced_options": "Opciones avanzadas",
        "weights": "Pesos internos: coverage={wc}, semantic={ws}",
        "cv_title": "CV",
        "upload_cv": "Sube tu CV (PDF, DOCX o TXT)",
        "paste_cv": "O pega el texto del CV",
        "paste_placeholder": "Pega aquí el contenido de tu CV…",
        "generate": "Generar Recomendaciones",
        "thinking_recommendations": "Pensando… generando recomendaciones personalizadas.",
        "loading_title": "CAIQ está analizando tu CV...",
        "loading_sub": "Calculando compatibilidad con roles de datos",
        "need_cv": "Sube un CV o pega texto para continuar.",
        "loading_model": "Cargando modelo...",
        "cv_extract_error": "No se pudo extraer texto del CV subido. Prueba con un PDF con texto seleccionable o pega el CV manualmente.",
        "skills_detected": "Skills en tu CV",
        "initial_gap": "Skills que te faltan",
        "remaining_gap": "Quedan tras la ruta",
        "target_profile": "Perfil objetivo: {role}",
        "skill_gap": "Skill gap",
        "masters_recommended": "Masters recomendados",
        "courses_recommended": "Cursos recomendados",
        "jobs_recommended": "Empleos recomendados",
        "jobs_applicable": "Empleos para aplicar ahora",
        "jobs_aspirational": "Empleos aspiracionales",
        "no_jobs_applicable": "No hay empleos claramente aplicables ahora mismo. Te mostramos opciones aspiracionales.",
        "jobs_blocked_non_data": "Actualmente no cumples el nivel mínimo para recomendar ofertas de empleo de este perfil con garantías. Te proponemos una ruta formativa para alcanzar ese nivel y volver a activar recomendaciones de empleo.",
        "jobs_unlocked_with_path": "Tu perfil todavía está en transición para este rol, pero con la ruta propuesta ya podemos mostrarte oportunidades realistas para empezar a aplicar de forma progresiva.",
        "jobs_readiness_stage": "Estado de preparación: {stage}",
        "readiness_no_base": "Sin base suficiente",
        "readiness_base": "Base inicial",
        "readiness_bridge": "Perfil puente",
        "readiness_ready": "Listo para empleo data",
        "plan_missing": "Plan por skill faltante",
        "generated": "Recomendaciones generadas.",
        "view_program": "Ver programa",
        "price": "Precio",
        "no_price": "Precio no especificado",
        "course_no_title": "Curso sin título",
        "course_rating": "Valoración: {rating} ({reviews} reseñas)",
        "duration": "Duración",
        "view_course": "Ver curso",
        "link_unavailable": "Enlace no disponible",
        "no_courses": "No hay cursos recomendados.",
        "no_jobs": "No hay empleos recomendados para este perfil.",
        "source": "Fuente",
        "go_offer": "Ir a oferta",
        "published_on": "Publicado: {value}",
        "badge_recent": "Reciente",
        "top_match": "Top Match",
        "top_n": "Top {n}",
        "goal_alignment_percent": "Alineación con tu objetivo {value}%",
        "goal_alignment_metric": "Alineación con tu objetivo: {value}%",
        "company_missing": "Empresa no indicada",
        "location_missing": "Ubicación no especificada",
        "job_no_title": "Puesto sin título",
        "no_skills_detected": "No se detectaron skills en el CV.",
        "no_masters": "No hay masters que cumplan los filtros.",
        "master_no_title": "Master sin nombre",
        "uni_missing": "Universidad no especificada",
        "missing_skill_none": "No hay skills faltantes para mapear cursos.",
        "missing_skill_no_course": "No hay cursos claros para esta skill en el catálogo actual.",
        "step1": "1. CV",
        "step2": "2. Filtros",
        "step3": "3. Resultados",
        "flow_title": "Cómo funciona",
        "quick_summary": "Resumen rápido",
        "best_job": "Mejor job",
        "next_course": "Siguiente curso",
        "top_gap_skills": "Skills clave a cerrar",
        "no_data": "Sin datos",
        "generate_hint": "Pulsa el botón para generar resultados con la configuración actual.",
        "live_price_beta": "Detectar precio en vivo",
        "live_price_note": "Intenta detectar automáticamente precios reales de cursos.",
        "geo_used": "Filtro geográfico aplicado: {country}",
        "geo_fallback": "No hubo resultados suficientes en {requested}. Se aplicó país cercano: {country}.",
        "match_index": "Match {value}/100",
        "match_percent": "Match {value}%",
        "coverage_component": "Cobertura de skills: {value}%",
        "semantic_component": "Cercanía al rol deseado: {value}%",
        "role_orientation_metric": "Orientación al rol: {value}",
        "role_orientation_high": "Alta",
        "role_orientation_medium": "Media",
        "role_orientation_low": "Baja",
        "job_match_profile": "Match con tu perfil: {value}%",
        "job_match_profile_level": "Match con tu perfil: {value}% ({level})",
        "match_level_very_high": "Muy alto",
        "match_level_high": "Alto",
        "match_level_medium": "Medio",
        "match_level_low": "Bajo",
        "score_note": "Índice para priorizar recomendaciones (no es probabilidad).",
        "sector_filter": "Sector preferido",
        "seniority_filter": "Seniority",
        "jobs_fallback_sector": "No hay empleos con el sector '{sector}' en este contexto. Se relajó ese filtro.",
        "jobs_fallback_seniority": "No hay empleos con seniority '{seniority}' en este contexto. Se relajó ese filtro.",
        "jobs_fallback_both": "No hay empleos con sector '{sector}' y seniority '{seniority}'. Se relajaron esos filtros.",
        "results_hub": "Panel de resultados",
        "fit_now": "Encaje actual con el rol",
        "fit_after": "Encaje estimado tras la ruta",
        "core_fit": "Cobertura núcleo del rol",
        "gap_after": "Gap restante estimado",
        "next_best_step": "Tu siguiente paso recomendado",
        "skills_intel": "Inteligencia de skills",
        "skills_detected_short": "Ya tienes",
        "skills_gap_short": "Te faltan",
        "skills_covered_short": "La ruta cubre",
        "inferred_skills_title": "Skills inferidas",
        "inferred_skills_empty": "No se han inferido skills adicionales.",
        "top_picks": "Recomendaciones clave",
        "explain_ai": "Por qué recomienda esto",
        "view_more": "Ver más",
        "all_masters": "Todos los masters",
        "all_courses": "Todos los cursos",
        "all_jobs": "Todos los empleos",
        "top_master": "Mejor máster",
        "top_course": "Mejor curso",
        "top_job": "Mejor empleo",
        "top_choice": "Recomendación principal",
        "profile_detected_summary": "Resumen del perfil detectado",
        "profile_detected": "Perfil detectado",
        "profile_strengths": "Fortalezas",
        "profile_gap_main": "Gap principal",
        "profile_focus": "Foco recomendado",
        "profile_focus_default": "Especialización técnica + experiencia aplicada",
        "data_master_detected": "Máster relevante en data detectado",
        "postgrad_status": "Posgrado detectado",
        "postgrad_data_yes": "Máster relacionado con data",
        "postgrad_master_non_data": "Máster no relacionado con data",
        "postgrad_none": "Sin máster detectado",
        "masters_context_has_data_master": "Ya cuentas con un máster relacionado con datos. No necesitas otro máster para avanzar de forma obligatoria; estas opciones son alternativas opcionales para especializarte o redirigir tu perfil según el rol objetivo.",
        "masters_context_has_master_non_data": "Hemos detectado que ya cuentas con un máster no especializado en data. Estas opciones son alternativas de especialización para una posible transición al rol objetivo.",
        "masters_context_no_master": "No hemos detectado máster en tu CV. Estas opciones pueden ser una vía formativa de alto impacto, junto con cursos y experiencia práctica.",
        "top_master_optional": "Máster opcional para profundizar",
        "top_master_bridge": "Máster para transición a data",
        "masters_recommended_optional": "Másteres opcionales para profundizar",
        "masters_recommended_bridge": "Másteres para transición a data",
        "upload_hint": "Sube tu CV para recibir recomendaciones personalizadas de habilidades, formación y oportunidades.",
        "upload_card_title": "Análisis de perfil con CV",
        "reco_reason": "Razón de recomendación",
        "covers_skills": "Skills que cubre",
        "reduces_gap": "Reducción de gap estimada",
        "impact_employability": "Impacto en empleabilidad",
        "best_balanced": "Más equilibrada",
        "fastest_option": "Más rápida",
        "premium_option": "Más completa",
        "highest_impact": "Mayor impacto",
        "coursera_reco": "Alternativas Coursera (coste)",
        "price_type": "Tipo de precio",
        "price_type_total_program": "Coste total del programa",
        "price_type_per_year": "Precio anual",
        "price_type_per_semester": "Precio por semestre",
        "price_type_per_credit": "Precio por crédito",
        "price_type_per_month": "Precio mensual",
        "price_type_per_course": "Precio por curso",
        "price_type_unknown": "Tipo no especificado",
        "show_less": "Ver menos",
        "skills_summary_line": "Tu CV ya recoge {detected} skills del rol. La ruta propuesta aborda las principales skills que te faltan.",
        "skills_summary_core_good": "Cubres una parte sólida de las habilidades troncales del rol.",
        "skills_summary_core_mid": "Tienes una base parcial del núcleo del rol; conviene reforzar varias skills clave.",
        "skills_summary_core_low": "Tu principal gap está en habilidades troncales del rol objetivo.",
        "skills_summary_missing_focus": "Te faltan principalmente herramientas complementarias y específicas.",
        "skills_summary_missing_advanced": "Tu principal gap está en skills técnicas avanzadas concretas.",
        "badge_rank_top": "Más directo al rol",
        "badge_rank_balanced": "Te aporta buen equilibrio",
        "badge_rank_fast": "Más rápido de completar",
        "badge_rank_complete": "Profundiza en el perfil",
        "badge_rank_job_top": "Puedes aplicar ya",
        "badge_rank_job_solid": "Encaja con tu momento",
        "badge_rank_job_aspirational": "Rol aspiracional",
        "badge_rank_top_tip": "Opción mejor orientada para acercarte al rol objetivo.",
        "badge_rank_balanced_tip": "Buena relación entre tiempo invertido y valor aportado.",
        "badge_rank_fast_tip": "Ruta ágil para progresar en menos tiempo.",
        "badge_rank_complete_tip": "Recorrido más profundo para consolidar conocimientos.",
        "badge_rank_job_top_tip": "Oferta con encaje alto para aplicar en el corto plazo.",
        "badge_rank_job_solid_tip": "Buena alternativa para avanzar con tu perfil actual.",
        "badge_rank_job_aspirational_tip": "Opción más exigente, válida como siguiente reto.",
        "provider": "Proveedor",
        "content_brief": "Resumen",
        "unknown_provider": "Proveedor no especificado",
        "reco_why_template": "Se recomienda porque {reason}.",
        "why_high_both": "combina alta cobertura de skills clave y alta alineación con el rol objetivo",
        "why_high_cov_mid_align": "cubre muchas skills clave, aunque su alineación con el rol es moderada",
        "why_mid_cov_high_align": "está muy alineado con el rol objetivo y refuerza skills técnicas prioritarias",
        "why_general": "presenta un equilibrio sólido entre cobertura, alineación y señales de calidad",
        "explain_reco_intro": "En formación usamos dos señales: Cobertura de skills y Cercanía al rol deseado. En empleos usamos Match con tu perfil para estimar qué tan viable es aplicar hoy.",
        "explain_reco_tooltip": "Formación: Cobertura + Cercanía al rol. Empleo: Match con tu perfil.",
        "label_direct_role": "Muy alineado al rol",
        "label_close_gaps": "Cubre gaps clave",
        "label_base_technical": "Base técnica sólida",
        "label_specialized": "Perfil especializado",
        "label_complementary": "Perfil más completo",
        "label_low_priority": "Impacto limitado",
        "training_label_high_alignment": "Muy alineado con tu objetivo",
        "training_label_good_goal": "Buena opción para tu objetivo",
        "training_label_complementary_option": "Opción complementaria",
        "training_message_strengthen_core": "No hemos encontrado programas formativos muy alineados con tu perfil por ahora. Te recomendamos reforzar primero tus skills base antes de pasar a programas especializados.",
        "insight_direct_role": "Muy buena opción: cubre carencias importantes y está claramente orientada al rol que buscas.",
        "insight_close_gaps": "Te ayuda a reforzar skills clave, aunque no es la vía más directa hacia el rol final.",
        "insight_base_technical": "Buena base técnica para consolidar fundamentos antes de dar el siguiente salto.",
        "insight_specialized": "Opción orientada al rol con foco más especializado para diferenciar tu perfil.",
        "insight_complementary": "Aporta valor como complemento del plan principal, con impacto moderado en tus gaps actuales.",
        "insight_low_priority": "Impacto limitado para tu objetivo actual; útil solo como opción secundaria.",
        "training_insight_high_alignment": "Contribuye de forma clara a tu transición hacia el rol objetivo.",
        "training_insight_good_goal": "Buena opción para avanzar hacia tu rol objetivo con una ruta razonable.",
        "training_insight_complementary_option": "Aporta valor como complemento a opciones más fuertes para tu objetivo.",
        "job_label_strong_fit": "Muy alineado con tu perfil",
        "job_label_good_fit": "Encaja con tu momento",
        "job_label_partial_fit": "Más exigente",
        "job_label_aspirational": "Rol aspiracional",
        "job_insight_strong_fit": "Muy alineado con tu perfil actual y con el tipo de rol que buscas.",
        "job_insight_good_fit": "Buena oportunidad según tu perfil, aunque algunos requisitos pueden hacerlo más exigente.",
        "job_insight_partial_fit": "Encaja de forma parcial con tu perfil; puede requerir experiencia adicional en algunos requisitos.",
        "job_insight_aspirational": "Rol aspiracional: encaja parcialmente con tu perfil actual.",
    },
    "en": {
        "hero_kicker": "Career Navigator",
        "hero_title": "Define your next step in Data, AI and Analytics",
        "hero_subtitle": "Discover which role fits you and which skills you need to grow in the data world.",
        "hero_cta_primary": "Analyze profile",
        "hero_cta_secondary": "How it works",
        "hero_chip_cv": "CV Matching",
        "hero_chip_gap": "Skill Gap Analysis",
        "hero_chip_masters": "Masters Recommendations",
        "hero_chip_jobs": "Jobs and Courses",
        "hero_chip_roadmap": "Professional Roadmap",
        "profile": "Profile",
        "target_role": "Target role",
        "filters": "Filters",
        "enable_price": "Enable price filter",
        "price_range": "Price range (EUR)",
        "price_range_comparable": "Comparable price range (EUR, total program cost)",
        "price_filtering": "Price filter: {min} - {max}",
        "include_no_price": "Include programs without price",
        "price_scope_note": "This filter uses only comparable prices (total program cost).",
        "country": "Country",
        "all_countries": "All",
        "city": "City / Location",
        "all_cities": "All",
        "quick_keyword": "Quick keyword",
        "none": "None",
        "any_option": "All",
        "manual_keyword": "Manual keyword",
        "manual_placeholder": "e.g., NLP, Deep Learning...",
        "advanced_options": "Advanced options",
        "weights": "Internal weights: coverage={wc}, semantic={ws}",
        "cv_title": "CV",
        "upload_cv": "Upload your CV (PDF, DOCX, or TXT)",
        "paste_cv": "Or paste CV text",
        "paste_placeholder": "Paste your CV text here…",
        "generate": "Generate Recommendations",
        "thinking_recommendations": "Thinking… generating personalized recommendations.",
        "loading_title": "CAIQ is analysing your CV...",
        "loading_sub": "Calculating compatibility with data roles",
        "need_cv": "Upload a CV or paste text to continue.",
        "loading_model": "Loading model...",
        "cv_extract_error": "Could not extract text from uploaded CV. Try a selectable-text PDF or paste the CV text manually.",
        "skills_detected": "Skills in your CV",
        "initial_gap": "Skills you're missing",
        "remaining_gap": "Remaining after path",
        "target_profile": "Target profile: {role}",
        "skill_gap": "Skill gap",
        "masters_recommended": "Recommended masters",
        "courses_recommended": "Recommended courses",
        "jobs_recommended": "Recommended jobs",
        "jobs_applicable": "Jobs you can apply to now",
        "jobs_aspirational": "Aspirational jobs",
        "no_jobs_applicable": "No clearly applicable jobs right now. Showing aspirational options.",
        "jobs_blocked_non_data": "Your profile does not currently meet the minimum level required to recommend jobs for this target profile with confidence. We suggest a learning path first to reach that level and then unlock job recommendations.",
        "jobs_unlocked_with_path": "Your profile is still in transition for this role, but with the proposed path we can already surface realistic opportunities to start applying progressively.",
        "jobs_readiness_stage": "Readiness stage: {stage}",
        "readiness_no_base": "No sufficient base",
        "readiness_base": "Initial base",
        "readiness_bridge": "Bridge profile",
        "readiness_ready": "Ready for data jobs",
        "plan_missing": "Plan by missing skill",
        "generated": "Recommendations generated.",
        "view_program": "View program",
        "price": "Price",
        "no_price": "Price not specified",
        "course_no_title": "Untitled course",
        "course_rating": "Rating: {rating} ({reviews} reviews)",
        "duration": "Duration",
        "view_course": "View course",
        "link_unavailable": "Link unavailable",
        "no_courses": "No recommended courses found.",
        "no_jobs": "No recommended jobs found for this profile.",
        "source": "Source",
        "go_offer": "Open job page",
        "published_on": "Posted: {value}",
        "badge_recent": "Recent",
        "top_match": "Top Match",
        "top_n": "Top {n}",
        "goal_alignment_percent": "Alignment with your goal {value}%",
        "goal_alignment_metric": "Alignment with your goal: {value}%",
        "company_missing": "Company not provided",
        "location_missing": "Location not provided",
        "job_no_title": "Untitled job",
        "no_skills_detected": "No skills detected from the CV.",
        "no_masters": "No masters match the current filters.",
        "master_no_title": "Untitled master",
        "uni_missing": "University not specified",
        "missing_skill_none": "No missing skills to map courses.",
        "missing_skill_no_course": "No clear course found for this skill in the current catalog.",
        "step1": "1. CV",
        "step2": "2. Filters",
        "step3": "3. Results",
        "flow_title": "How it works",
        "quick_summary": "Quick summary",
        "best_job": "Best job",
        "next_course": "Next course",
        "top_gap_skills": "Key gap skills",
        "no_data": "No data",
        "generate_hint": "Click the button to generate results with the current settings.",
        "live_price_beta": "Detect live price",
        "live_price_note": "Automatically tries to detect real course prices.",
        "geo_used": "Applied geographic filter: {country}",
        "geo_fallback": "Not enough results in {requested}. Using nearest fallback country: {country}.",
        "match_index": "Match {value}/100",
        "match_percent": "Match {value}%",
        "coverage_component": "Skill coverage: {value}%",
        "semantic_component": "Target-role closeness: {value}%",
        "role_orientation_metric": "Role orientation: {value}",
        "role_orientation_high": "High",
        "role_orientation_medium": "Medium",
        "role_orientation_low": "Low",
        "job_match_profile": "Profile match: {value}%",
        "job_match_profile_level": "Profile match: {value}% ({level})",
        "match_level_very_high": "Very high",
        "match_level_high": "High",
        "match_level_medium": "Medium",
        "match_level_low": "Low",
        "score_note": "Priority index for ranking recommendations (not a probability).",
        "sector_filter": "Preferred sector",
        "seniority_filter": "Seniority",
        "jobs_fallback_sector": "No jobs found for sector '{sector}' in this context. Sector filter was relaxed.",
        "jobs_fallback_seniority": "No jobs found for seniority '{seniority}' in this context. Seniority filter was relaxed.",
        "jobs_fallback_both": "No jobs found for sector '{sector}' and seniority '{seniority}'. Both filters were relaxed.",
        "results_hub": "Results Hub",
        "fit_now": "Current role fit",
        "fit_after": "Estimated fit after path",
        "core_fit": "Role core coverage",
        "gap_after": "Estimated remaining gap",
        "next_best_step": "Your recommended next step",
        "skills_intel": "Skills intelligence",
        "skills_detected_short": "You have",
        "skills_gap_short": "Missing",
        "skills_covered_short": "Path covers",
        "inferred_skills_title": "Inferred skills",
        "inferred_skills_empty": "No additional inferred skills.",
        "top_picks": "Key recommendations",
        "explain_ai": "Why AI recommends this",
        "view_more": "View more",
        "all_masters": "All masters",
        "all_courses": "All courses",
        "all_jobs": "All jobs",
        "top_master": "Best master",
        "top_course": "Best course",
        "top_job": "Best job",
        "top_choice": "Primary recommendation",
        "profile_detected_summary": "Detected profile summary",
        "profile_detected": "Detected profile",
        "profile_strengths": "Strengths",
        "profile_gap_main": "Main gap",
        "profile_focus": "Recommended focus",
        "profile_focus_default": "Technical specialization + applied experience",
        "data_master_detected": "Relevant data master detected",
        "postgrad_status": "Detected postgraduate status",
        "postgrad_data_yes": "Data-related master",
        "postgrad_master_non_data": "Non-data master",
        "postgrad_none": "No master detected",
        "masters_context_has_data_master": "You already have a data-related master. You do not strictly need another one to progress; these are optional alternatives to specialize or pivot your profile for the target role.",
        "masters_context_has_master_non_data": "We detected that you already have a non-data specialized master. These options are specialization alternatives for a potential transition into your target role.",
        "masters_context_no_master": "We did not detect a master in your CV. These options can be a high-impact learning path together with courses and practical experience.",
        "top_master_optional": "Optional master to deepen skills",
        "top_master_bridge": "Master for transition to data",
        "masters_recommended_optional": "Optional masters to deepen skills",
        "masters_recommended_bridge": "Masters for transition to data",
        "upload_hint": "Upload your CV to receive personalized recommendations for skills, learning, and opportunities.",
        "upload_card_title": "CV-based profile analysis",
        "reco_reason": "Recommendation rationale",
        "covers_skills": "Skills covered",
        "reduces_gap": "Estimated gap reduction",
        "impact_employability": "Employability impact",
        "best_balanced": "Most balanced",
        "fastest_option": "Fastest path",
        "premium_option": "Most complete",
        "highest_impact": "Highest impact",
        "coursera_reco": "Coursera alternatives (cost)",
        "price_type": "Price type",
        "price_type_total_program": "Total program cost",
        "price_type_per_year": "Per year",
        "price_type_per_semester": "Per semester",
        "price_type_per_credit": "Per credit",
        "price_type_per_month": "Per month",
        "price_type_per_course": "Per course",
        "price_type_unknown": "Unspecified type",
        "show_less": "Show less",
        "skills_summary_line": "Your CV already covers {detected} skills for this role. The proposed path addresses the main skills you are missing.",
        "skills_summary_core_good": "You already cover a solid share of the role's core skills.",
        "skills_summary_core_mid": "You have a partial base of the role core; reinforcing key skills is recommended.",
        "skills_summary_core_low": "Your main gap is in the core skills required for the target role.",
        "skills_summary_missing_focus": "Most remaining gaps are complementary and tool-specific skills.",
        "skills_summary_missing_advanced": "Your main gap is in concrete advanced technical skills.",
        "badge_rank_top": "Most direct to the role",
        "badge_rank_balanced": "Balanced value for your time",
        "badge_rank_fast": "Fastest to complete",
        "badge_rank_complete": "Deepens your profile",
        "badge_rank_job_top": "You can apply now",
        "badge_rank_job_solid": "Fits your current stage",
        "badge_rank_job_aspirational": "Aspirational role",
        "badge_rank_top_tip": "Option best oriented to your target role.",
        "badge_rank_balanced_tip": "Solid balance between effort and expected value.",
        "badge_rank_fast_tip": "Faster route to progress in skills.",
        "badge_rank_complete_tip": "Path with deeper coverage of core topics.",
        "badge_rank_job_top_tip": "High-fit job to apply for in the short term.",
        "badge_rank_job_solid_tip": "Strong option to progress with your current profile.",
        "badge_rank_job_aspirational_tip": "More demanding role, useful as your next target.",
        "provider": "Provider",
        "content_brief": "Summary",
        "unknown_provider": "Provider not specified",
        "reco_why_template": "Recommended because {reason}.",
        "why_high_both": "it combines high key-skill coverage with high role alignment",
        "why_high_cov_mid_align": "it covers many key skills, although role alignment is moderate",
        "why_mid_cov_high_align": "it is strongly aligned with your target role while reinforcing priority technical skills",
        "why_general": "it offers a strong balance across coverage, alignment, and quality signals",
        "explain_reco_intro": "For learning options we use two signals: Skill coverage and Target-role closeness. For jobs we use Profile match to estimate how viable it is to apply today.",
        "explain_reco_tooltip": "Learning: Coverage + Role closeness. Jobs: Profile match.",
        "label_direct_role": "Highly role-aligned",
        "label_close_gaps": "Covers key gaps",
        "label_base_technical": "Strong technical base",
        "label_specialized": "Specialized profile",
        "label_complementary": "Broader profile",
        "label_low_priority": "Limited impact",
        "training_label_high_alignment": "Highly aligned with your goal",
        "training_label_good_goal": "Good option for your goal",
        "training_label_complementary_option": "Complementary option",
        "training_message_strengthen_core": "We could not find highly aligned training programs for your profile yet. We recommend strengthening your core skills before pursuing specialized programs.",
        "insight_direct_role": "Strong option: closes important gaps and is clearly oriented to your target role.",
        "insight_close_gaps": "Helps reinforce key skills, though it is not the most direct route to the role.",
        "insight_base_technical": "Solid technical base to consolidate fundamentals before the next step.",
        "insight_specialized": "Role-oriented option with a more specialized focus to differentiate your profile.",
        "insight_complementary": "Useful as a complement to your main path, with moderate impact on current gaps.",
        "insight_low_priority": "Limited impact for your current goal; better as a secondary option.",
        "training_insight_high_alignment": "It contributes clearly to your transition toward the target role.",
        "training_insight_good_goal": "A good option to progress toward your target role with a realistic path.",
        "training_insight_complementary_option": "It adds value as a complement to stronger options for your goal.",
        "job_label_strong_fit": "Highly aligned with your profile",
        "job_label_good_fit": "Fits your current stage",
        "job_label_partial_fit": "More demanding",
        "job_label_aspirational": "Aspirational role",
        "job_insight_strong_fit": "Highly aligned with your current profile and the role you are targeting.",
        "job_insight_good_fit": "Good opportunity for your profile, though some requirements may be more demanding.",
        "job_insight_partial_fit": "Partially aligned with your profile; some requirements may need extra experience.",
        "job_insight_aspirational": "Aspirational role: partially aligned with your current profile.",
    },
}


def tr(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "es")
    base = I18N.get(lang, I18N["es"]).get(key, I18N["es"].get(key, key))
    return base.format(**kwargs) if kwargs else base


def _stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def parse_price_token(token: str) -> float | None:
    t = str(token or "").strip()
    if not t:
        return None
    t = re.sub(r"[^\d,.\-]", "", t)
    if not t:
        return None

    # 14.865 or 14,865 -> 14865
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", t):
        return float(re.sub(r"[.,]", "", t))

    # 14999 or 14999.50 or 14999,50
    if re.fullmatch(r"\d+[.,]\d{1,2}", t):
        return float(t.replace(",", "."))
    if re.fullmatch(r"\d+", t):
        return float(t)

    # 14,865.50 or 14.865,50
    if "," in t and "." in t:
        if t.rfind(".") > t.rfind(","):
            return float(t.replace(",", ""))
        return float(t.replace(".", "").replace(",", "."))

    return None


def parse_price_from_tuition(tuition: str) -> float | None:
    txt = str(tuition or "").strip()
    if not txt:
        return None
    if "free" in txt.lower():
        return None
    m = re.search(r"(\d[\d.,]*)", txt)
    if not m:
        return None
    return parse_price_token(m.group(1))


# Tasas de conversión a EUR usadas para mostrar precios orientativos.
# Fuente: Banco Central Europeo / XE.com — tasas aproximadas a mayo 2026.
# NOTA: estos valores son estáticos; los precios mostrados en la app son
# orientativos y pueden diferir del precio real según la fecha de consulta.
# Actualizar manualmente si se detectan desviaciones superiores al 10%.
FX_TO_EUR = {
    "EUR": 1.00,
    "USD": 0.92,
    "GBP": 1.17,
    "CHF": 1.04,
    "AUD": 0.61,
    "CAD": 0.68,
    "NZD": 0.56,
    "SEK": 0.09,
    "NOK": 0.09,
    "DKK": 0.13,
    "PLN": 0.23,
    "CZK": 0.04,
    "HUF": 0.0025,
    "RON": 0.20,
    "TRY": 0.028,
    "INR": 0.011,
    "JPY": 0.0062,
    "CNY": 0.127,
    "HKD": 0.118,
    "SGD": 0.69,
    "AED": 0.25,
    "MXN": 0.050,
    "BRL": 0.17,
    "ZAR": 0.048,
    "KRW": 0.00068,
}


def detect_currency_from_tuition(tuition: str) -> str:
    txt = str(tuition or "").upper()
    if not txt:
        return "EUR"
    patterns = [
        ("EUR", [r"\bEUR\b", "€"]),
        ("USD", [r"\bUSD\b", r"\$"]),
        ("GBP", [r"\bGBP\b", "£"]),
        ("CHF", [r"\bCHF\b"]),
        ("AUD", [r"\bAUD\b"]),
        ("CAD", [r"\bCAD\b"]),
        ("NZD", [r"\bNZD\b"]),
        ("SEK", [r"\bSEK\b"]),
        ("NOK", [r"\bNOK\b"]),
        ("DKK", [r"\bDKK\b"]),
        ("PLN", [r"\bPLN\b"]),
        ("CZK", [r"\bCZK\b"]),
        ("HUF", [r"\bHUF\b"]),
        ("RON", [r"\bRON\b"]),
        ("TRY", [r"\bTRY\b"]),
        ("INR", [r"\bINR\b"]),
        ("JPY", [r"\bJPY\b", "¥"]),
        ("CNY", [r"\bCNY\b", r"\bRMB\b"]),
        ("HKD", [r"\bHKD\b"]),
        ("SGD", [r"\bSGD\b"]),
        ("AED", [r"\bAED\b"]),
        ("MXN", [r"\bMXN\b"]),
        ("BRL", [r"\bBRL\b"]),
        ("ZAR", [r"\bZAR\b"]),
        ("KRW", [r"\bKRW\b"]),
    ]
    for code, pats in patterns:
        for p in pats:
            if re.search(p, txt):
                return code
    return "EUR"


def convert_to_eur(amount: float, currency: str) -> float:
    rate = FX_TO_EUR.get(str(currency or "").upper(), 1.0)
    return float(amount) * float(rate)


def normalize_master_price_value(price_value, tuition) -> float | None:
    parsed_tuition = parse_price_from_tuition(tuition)
    # If tuition has a reliable parsed value, prioritize it.
    if parsed_tuition is not None:
        curr = detect_currency_from_tuition(tuition)
        return float(convert_to_eur(parsed_tuition, curr))
    if pd.isna(price_value):
        return None
    return float(price_value)


def detect_master_price_type(tuition: str) -> str:
    txt = str(tuition or "").strip().lower()
    if not txt:
        return "unknown"
    if "per credit" in txt or "por credito" in txt or "por crédito" in txt:
        return "per_credit"
    if "per semester" in txt or "per term" in txt or "por semestre" in txt:
        return "per_semester"
    if "per month" in txt or "monthly" in txt or "por mes" in txt:
        return "per_month"
    if "per year" in txt or "yearly" in txt or "por año" in txt or "por ano" in txt:
        return "per_year"
    if "per course" in txt or "por curso" in txt:
        return "per_course"
    # If no periodic indicator is present, treat it as total program cost.
    return "total_program"


def comparable_master_price_eur(row: pd.Series) -> float | None:
    val = normalize_master_price_value(row.get("price_value_eur"), row.get("tuition"))
    if val is None:
        return None
    ptype = detect_master_price_type(row.get("tuition", ""))
    if ptype != "total_program":
        return None
    # Plausibility bounds to drop parsing glitches and unrealistic outliers.
    if val < 100 or val > 200000:
        return None
    return float(val)


def master_price_type_label(price_type: str) -> str:
    key = f"price_type_{str(price_type or 'unknown').lower()}"
    return tr(key)


def master_price_label(row: pd.Series) -> str:
    val = normalize_master_price_value(row.get("price_value_eur"), row.get("tuition"))
    if val is None:
        return tr("no_price")
    ptype = detect_master_price_type(row.get("tuition", ""))
    type_lbl = master_price_type_label(ptype)
    return f"{f'{val:,.0f} EUR'.replace(',', '.')} · {type_lbl}"


@st.cache_resource
def load_model_module(model_version: float):
    module_path = ETL_DIR / "pipelines" / "build_datapath_model_advanced.py"
    return load_module(module_path, f"datapath_model_app_{int(model_version)}")


def filter_visible_jobs_for_app(jobs_feat: pd.DataFrame, max_age_days: int = MAX_VISIBLE_JOB_AGE_DAYS) -> pd.DataFrame:
    if jobs_feat is None or jobs_feat.empty or "date_posted" not in jobs_feat.columns:
        return jobs_feat

    posted_dt = pd.to_datetime(jobs_feat["date_posted"], errors="coerce")
    now = pd.Timestamp.now()
    cutoff = now - pd.Timedelta(days=max_age_days)
    mask = posted_dt.notna() & (posted_dt >= cutoff) & (posted_dt <= now + pd.Timedelta(days=1))
    if "url_status" in jobs_feat.columns:
        mask = mask & jobs_feat["url_status"].fillna("unknown").astype(str).str.lower().ne("dead")
    return jobs_feat.loc[mask].reset_index(drop=True)


@st.cache_data
def load_data():
    masters_feat = pd.read_csv(ETL_DIR / "outputs" / "semantic" / "masters_features.csv")
    masters_feat["price_value_eur"] = masters_feat.apply(
        lambda r: normalize_master_price_value(r.get("price_value_eur"), r.get("tuition")), axis=1
    )
    masters_feat["price_type"] = masters_feat.get("tuition", "").map(detect_master_price_type)
    masters_feat["price_comparable_eur"] = masters_feat.apply(comparable_master_price_eur, axis=1)
    courses_feat = pd.read_csv(ETL_DIR / "outputs" / "semantic" / "courses_features.csv")
    manual_prices_path = ETL_DIR / "outputs" / "semantic" / "course_prices_manual.csv"
    if manual_prices_path.exists():
        manual_prices = pd.read_csv(manual_prices_path)
        keep_cols = [c for c in ["course_id", "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE"] if c in manual_prices.columns]
        if keep_cols:
            courses_feat = courses_feat.merge(
                manual_prices[keep_cols].drop_duplicates(subset=["course_id"]),
                on="course_id",
                how="left",
                suffixes=("", "_manual"),
            )
    prices_cache_path = ETL_DIR / "outputs" / "semantic" / "course_prices_scraped.csv"
    if prices_cache_path.exists():
        prices_cache = pd.read_csv(prices_cache_path)
        keep_cols = [c for c in ["course_id", "price_text", "price_value_eur", "price_source"] if c in prices_cache.columns]
        if keep_cols:
            courses_feat = courses_feat.merge(
                prices_cache[keep_cols].drop_duplicates(subset=["course_id"]),
                on="course_id",
                how="left",
                suffixes=("", "_scraped"),
            )
    jobs_v2_path = ETL_DIR / "outputs" / "semantic" / "jobs_features_v2.csv"
    jobs_base_path = ETL_DIR / "outputs" / "semantic" / "jobs_features.csv"
    jobs_feat = pd.read_csv(jobs_v2_path if jobs_v2_path.exists() else jobs_base_path)
    jobs_curated_path = ETL_DIR / "outputs" / "curated" / "job_postings_clean.csv"
    if jobs_curated_path.exists() and "date_posted" not in jobs_feat.columns and "job_id" in jobs_feat.columns:
        jobs_curated = pd.read_csv(jobs_curated_path, usecols=lambda c: c in {"job_id", "date_posted"})
        if not jobs_curated.empty and "job_id" in jobs_curated.columns and "date_posted" in jobs_curated.columns:
            jobs_feat = jobs_feat.merge(
                jobs_curated.drop_duplicates(subset=["job_id"]),
                on="job_id",
                how="left",
            )
    job_url_status_path = ETL_DIR / "outputs" / "semantic" / "job_url_status.csv"
    if job_url_status_path.exists() and "job_url" in jobs_feat.columns:
        job_url_status = pd.read_csv(job_url_status_path, usecols=lambda c: c in {"job_url", "url_status", "last_checked_at"})
        if not job_url_status.empty and "job_url" in job_url_status.columns:
            jobs_feat = jobs_feat.merge(
                job_url_status.drop_duplicates(subset=["job_url"], keep="last"),
                on="job_url",
                how="left",
                suffixes=("", "_status"),
            )
            if "url_status_status" in jobs_feat.columns:
                jobs_feat["url_status"] = jobs_feat["url_status_status"].combine_first(jobs_feat.get("url_status"))
                jobs_feat = jobs_feat.drop(columns=["url_status_status"])
            if "last_checked_at_status" in jobs_feat.columns:
                jobs_feat["last_checked_at"] = jobs_feat["last_checked_at_status"].combine_first(jobs_feat.get("last_checked_at"))
                jobs_feat = jobs_feat.drop(columns=["last_checked_at_status"])
    jobs_feat = filter_visible_jobs_for_app(jobs_feat)
    role_skill_demand = pd.read_csv(ETL_DIR / "outputs" / "semantic" / "role_skill_demand.csv")
    # Use pre-augmented skills files (generated once; ~3x more coverage) when available.
    _ms_aug = ETL_DIR / "outputs" / "curated" / "master_skills_augmented.csv"
    _cs_aug = ETL_DIR / "outputs" / "curated" / "course_skills_augmented.csv"
    master_skills = pd.read_csv(_ms_aug if _ms_aug.exists() else ETL_DIR / "outputs" / "curated" / "master_skills.csv")
    course_skills = pd.read_csv(_cs_aug if _cs_aug.exists() else ETL_DIR / "outputs" / "curated" / "course_skills.csv")
    coursera_prices_data_path = ETL_DIR / "outputs" / "semantic" / "coursera_courses_prices_data.csv"
    coursera_prices_path = ETL_DIR / "outputs" / "semantic" / "coursera_courses_prices.csv"
    coursera_prices = pd.read_csv(coursera_prices_data_path if coursera_prices_data_path.exists() else coursera_prices_path) if (coursera_prices_data_path.exists() or coursera_prices_path.exists()) else pd.DataFrame()
    job_skills = pd.read_csv(ETL_DIR / "outputs" / "curated" / "job_skills.csv")
    taxonomy = json.loads((ETL_DIR / "config" / "skills_taxonomy.json").read_text(encoding="utf-8-sig"))

    tuned = {"weight_coverage": 0.65, "weight_semantic": 0.35}
    tuned_path = ETL_DIR / "reports" / "model_tuned_params.json"
    if tuned_path.exists():
        tuned.update(json.loads(tuned_path.read_text(encoding="utf-8")))

    return {
        "masters_feat": masters_feat,
        "courses_feat": courses_feat,
        "jobs_feat": jobs_feat,
        "role_skill_demand": role_skill_demand,
        "master_skills": master_skills,
        "course_skills": course_skills,
        "coursera_prices": coursera_prices,
        "job_skills": job_skills,
        "taxonomy": taxonomy,
        "tuned": tuned,
    }


@st.cache_resource
def get_catalog_embeddings(_mod, _data):
    masters_feat = (_data or {}).get("masters_feat", pd.DataFrame()).copy()
    courses_feat = (_data or {}).get("courses_feat", pd.DataFrame()).copy()

    m_texts = masters_feat.get("master_text", pd.Series(dtype=str)).fillna("").astype(str).tolist()
    c_texts = courses_feat.get("course_text", pd.Series(dtype=str)).fillna("").astype(str).tolist()

    master_embs, master_mode = _mod.embed_texts(m_texts) if m_texts else ([], "none")
    course_embs, course_mode = _mod.embed_texts(c_texts) if c_texts else ([], "none")

    # When in TF-IDF mode, rebuild with an explicit vectorizer so query texts
    # can be transformed into the SAME feature space as the catalog embeddings.
    # Without this, embed_texts([gap_text]) creates a mismatched vocabulary.
    master_vectorizer = None
    course_vectorizer = None
    if master_mode == "tfidf" and m_texts:
        from sklearn.feature_extraction.text import TfidfVectorizer
        master_vectorizer = TfidfVectorizer(max_features=40000, ngram_range=(1, 2))
        master_embs = master_vectorizer.fit_transform(m_texts)
    if course_mode == "tfidf" and c_texts:
        from sklearn.feature_extraction.text import TfidfVectorizer
        course_vectorizer = TfidfVectorizer(max_features=40000, ngram_range=(1, 2))
        course_embs = course_vectorizer.fit_transform(c_texts)

    master_id_to_idx = {
        str(mid): idx for idx, mid in enumerate(masters_feat.get("master_id", pd.Series(dtype=object)).tolist())
    }
    course_id_to_idx = {
        str(cid): idx for idx, cid in enumerate(courses_feat.get("course_id", pd.Series(dtype=object)).tolist())
    }

    return {
        "master_embeddings": master_embs,
        "master_texts": m_texts,
        "master_emb_mode": master_mode,
        "master_id_to_idx": master_id_to_idx,
        "master_vectorizer": master_vectorizer,
        "course_embeddings": course_embs,
        "course_texts": c_texts,
        "course_emb_mode": course_mode,
        "course_id_to_idx": course_id_to_idx,
        "course_vectorizer": course_vectorizer,
    }


@st.cache_resource
def warmup_nlp_pipeline(_mod, _taxonomy):
    """
    Pre-compila las funciones NLP en el arranque de la app.
    Sin esto, la primera llamada a build_candidate_profile_hybrid tarda ~1.5 s
    porque Python JIT-compila regex, patrones y estructuras internas.
    Con el warm-up el cold start queda en ~150 ms.
    """
    try:
        _dummy = (
            "Data Scientist Python SQL Machine Learning Scikit-learn "
            "Pandas NumPy TensorFlow Docker AWS 3 years experience"
        )
        _mod.build_candidate_profile_hybrid(_dummy, _taxonomy)
    except Exception:
        pass  # el warm-up falla silenciosamente; no es crítico


def load_tuned_config_only():
    tuned = {"weight_coverage": 0.65, "weight_semantic": 0.35}
    tuned_path = ETL_DIR / "reports" / "model_tuned_params.json"
    if tuned_path.exists():
        tuned.update(json.loads(tuned_path.read_text(encoding="utf-8")))
    return tuned


def extract_candidate_name(resume_text: str) -> str:
    """Extrae el nombre del candidato de las primeras líneas del CV."""
    if not resume_text:
        return ""
    import re
    lines = [l.strip() for l in resume_text.splitlines() if l.strip()]
    # Busca en las primeras 8 líneas
    for line in lines[:8]:
        # Descarta líneas que parezcan emails, teléfonos, URLs o títulos largos
        if any(x in line.lower() for x in ["@", "http", "linkedin", "github", "tel:", "phone", "email"]):
            continue
        if len(line) > 60 or len(line) < 3:
            continue
        # Solo letras, espacios y caracteres de nombre (tildes, guiones)
        if re.match(r"^[A-Za-záéíóúüñÁÉÍÓÚÜÑàèìòùâêîôûäëïöüçÇ\s'\-]+$", line):
            words = line.split()
            # Un nombre tiene entre 2 y 5 palabras
            if 2 <= len(words) <= 5:
                return line.title()
    return ""


def humanize_label(value: str) -> str:
    txt = re.sub(r"[_\-]+", " ", str(value or "").strip())
    return re.sub(r"\s+", " ", txt).title()


def format_price_eur(value) -> str:
    if pd.isna(value):
        return tr("no_price")
    return f"{float(value):,.0f} EUR".replace(",", ".")


def compact_text(value: str, max_len: int = 180) -> str:
    txt = re.sub(r"\s+", " ", str(value or "").strip())
    return txt if len(txt) <= max_len else txt[: max_len - 1] + "…"


def clean_ui_text(value: str) -> str:
    txt = html.unescape(str(value or ""))
    txt = re.sub(r"<[^>]+>", " ", txt)
    # Hide dataset placeholders that should never be shown to users.
    txt = re.sub(r"\bCONTENT_UNAVAILABLE\b", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bN/?A\b", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\s*,\s*,+", ", ", txt)
    txt = re.sub(r"\s+,", ",", txt)
    txt = re.sub(r"\s+\|\s+", " | ", txt)
    txt = re.sub(r"(?:\s*\|\s*){2,}", " | ", txt)
    txt = txt.strip(" |,;:-")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def parse_job_posted_date(value) -> pd.Timestamp | None:
    txt = str(value or "").strip()
    if not txt:
        return None
    dt = pd.to_datetime(txt, errors="coerce", utc=True)
    if pd.isna(dt):
        dt = pd.to_datetime(txt, errors="coerce")
    if pd.isna(dt):
        return None
    if getattr(dt, "tzinfo", None) is not None:
        try:
            dt = dt.tz_convert(None)
        except Exception:
            dt = dt.tz_localize(None)
    # Guard against clearly invalid / legacy scraped dates.
    now = pd.Timestamp.now()
    if dt < pd.Timestamp(year=2025, month=1, day=1):
        return None
    if dt > now + pd.Timedelta(days=7):
        return None
    return dt


def format_job_posted_date(value) -> str:
    dt = parse_job_posted_date(value)
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def is_recent_job(value, max_days: int = 7) -> bool:
    dt = parse_job_posted_date(value)
    if dt is None:
        return False
    now = pd.Timestamp.now()
    delta_days = (now - dt).days
    return 0 <= delta_days <= max_days


def build_learning_content_snippet(row: pd.Series, reco_type: str, title: str, max_len: int = 120) -> str:
    if reco_type == "master":
        candidates = [row.get("study_content"), row.get("master_text")]
    elif reco_type == "course":
        candidates = [row.get("headline"), row.get("description"), row.get("course_text")]
    else:
        return ""

    title_clean = clean_ui_text(title).lower()
    for raw in candidates:
        txt = clean_ui_text(raw)
        if not txt or txt.lower() in {"nan", "none"}:
            continue

        if title_clean and txt.lower().startswith(title_clean):
            txt = txt[len(clean_ui_text(title)) :].lstrip(" -|:,.")
        if not txt or txt.lower() == title_clean:
            continue

        txt = txt.replace("|", " · ")
        txt = re.sub(r"\s*·\s*", " · ", txt)

        if " · " in txt:
            parts = [p.strip() for p in txt.split(" · ") if p.strip()]
            txt = ", ".join(parts[:3])
        else:
            txt = re.split(r"(?<=[.!?])\s+", txt)[0]

        txt = compact_text(txt, max_len=max_len)
        if len(txt) >= 20:
            return txt
    return ""


def prettify_job_label(value: str) -> str:
    txt = clean_ui_text(value)
    if not txt:
        return ""
    role_map = {
        "ml_engineer": "Machine Learning Engineer",
        "machine_learning_engineer": "Machine Learning Engineer",
        "data_engineer": "Data Engineer",
        "data_scientist": "Data Scientist",
        "data_analyst": "Data Analyst",
        "bi_analyst": "BI Analyst",
        "bi_engineer": "BI Engineer",
        "analytics_engineer": "Analytics Engineer",
        "mlops_engineer": "MLOps Engineer",
        "ai_engineer": "AI Engineer",
        "nlp_engineer": "NLP Engineer",
    }
    key = txt.strip().lower().replace("-", "_").replace(" ", "_")
    if key in role_map:
        return role_map[key]
    pretty = humanize_label(txt)
    replacements = {
        "Ml ": "ML ",
        " Ai ": " AI ",
        " Bi ": " BI ",
        "Nlp": "NLP",
        "LlM": "LLM",
        "MlopS": "MLOps",
    }
    for old, new in replacements.items():
        pretty = pretty.replace(old, new)
    return pretty.strip()


def build_job_content_snippet(row: pd.Series, max_len: int = 112) -> str:
    parts: list[str] = []
    role_family = prettify_job_label(row.get("role_family", ""))
    seniority = prettify_job_label(row.get("seniority", row.get("job_level", "")))
    work_mode = prettify_job_label(row.get("work_mode", ""))
    employment_type = prettify_job_label(row.get("employment_type", ""))
    language_req = prettify_job_label(row.get("language_requirements", ""))

    if role_family and role_family.lower() not in {"nan", "none", "unknown"}:
        parts.append(role_family)
    if seniority and seniority.lower() not in {"nan", "none", "unknown"}:
        parts.append(seniority)
    if work_mode and work_mode.lower() not in {"nan", "none", "unknown"}:
        parts.append(work_mode)
    if employment_type and employment_type.lower() not in {"nan", "none", "unknown"}:
        parts.append(employment_type)
    if language_req and language_req.lower() not in {"nan", "none", "unknown"}:
        parts.append(language_req)

    if len(parts) < 2:
        return ""
    return compact_text(" · ".join(parts[:3]), max_len=max_len)


_US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}
_COUNTRY_ALIAS = {
    "USA": "United States",
    "US": "United States",
    "United States of America": "United States",
    "UK": "United Kingdom",
    "U.K.": "United Kingdom",
    **{state: "United States" for state in _US_STATES},
}

_INVALID_COUNTRY_PAT = re.compile(
    r"\b(master|masters|degree|course|program|programme|science|university|school|bachelor|mba|msc|phd)\b",
    re.IGNORECASE,
)


def _clean_country_label(label: str) -> str:
    txt = str(label or "").strip()
    if not txt:
        return ""
    txt = _COUNTRY_ALIAS.get(txt, txt)
    low = txt.lower()
    if low in {"online", "multiple locations", "remote", "hybrid"}:
        return ""
    if _INVALID_COUNTRY_PAT.search(txt):
        return ""
    if any(ch.isdigit() for ch in txt):
        return ""
    if len(txt) > 40 or len(txt.split()) > 5:
        return ""
    return txt


def extract_country_from_location(location: str) -> str:
    txt = str(location or "").strip()
    if not txt:
        return ""
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    raw = parts[-1] if parts else txt
    return _clean_country_label(raw)


NEAREST_COUNTRY_MAP = {
    "Spain": ["Portugal", "France", "Italy"],
    "Portugal": ["Spain", "France"],
    "France": ["Spain", "Belgium", "Germany", "Italy"],
    "Italy": ["France", "Spain", "Germany"],
    "Germany": ["France", "Netherlands", "Belgium"],
    "Netherlands": ["Belgium", "Germany", "France"],
    "Belgium": ["Netherlands", "France", "Germany"],
    "United Kingdom": ["Ireland", "France", "Netherlands"],
    "Ireland": ["United Kingdom", "France"],
    "United States": ["Canada", "Mexico", "United Kingdom"],
    "Canada": ["United States", "United Kingdom"],
    "Mexico": ["United States", "Spain"],
}


def apply_country_fallback(
    selected_country: str,
    masters_df: pd.DataFrame,
    jobs_df: pd.DataFrame,
    target_role: str,
):
    if not selected_country or selected_country == tr("all_countries"):
        return masters_df, jobs_df, "", False

    m = masters_df.copy()
    j = jobs_df.copy()
    m["__country"] = m["location"].fillna("").astype(str).map(extract_country_from_location)
    j["__country"] = j["location"].fillna("").astype(str).map(extract_country_from_location)

    candidate_countries = [selected_country] + NEAREST_COUNTRY_MAP.get(selected_country, [])
    role_mask = j["role_family"].fillna("").str.lower() == str(target_role).lower()
    if not role_mask.any():
        role_mask = pd.Series([True] * len(j), index=j.index)

    for country in candidate_countries:
        m_f = m[m["__country"].str.lower() == country.lower()].copy()
        j_f = j[(j["__country"].str.lower() == country.lower()) & role_mask].copy()
        if len(m_f) > 0 and len(j_f) > 0:
            return m_f.drop(columns=["__country"]), j_f.drop(columns=["__country"]), country, country.lower() != selected_country.lower()

    for country in candidate_countries:
        m_f = m[m["__country"].str.lower() == country.lower()].copy()
        j_f = j[(j["__country"].str.lower() == country.lower()) & role_mask].copy()
        if len(m_f) > 0 or len(j_f) > 0:
            return m_f.drop(columns=["__country"]), j_f.drop(columns=["__country"]), country, country.lower() != selected_country.lower()

    return masters_df, jobs_df, selected_country, False


def apply_job_preference_fallback(jobs_df: pd.DataFrame, selected_sector: str, selected_seniority: str):
    jobs = jobs_df.copy()
    want_sector = selected_sector != tr("any_option") and "sector" in jobs.columns
    want_seniority = selected_seniority != tr("any_option") and "seniority" in jobs.columns

    if not want_sector and not want_seniority:
        return jobs, []

    messages = []
    if want_sector and want_seniority:
        both = jobs[
            jobs["sector"].fillna("").astype(str).str.lower().eq(selected_sector.lower())
            & jobs["seniority"].fillna("").astype(str).str.lower().eq(selected_seniority.lower())
        ]
        if len(both) > 0:
            return both, messages

        only_sector = jobs[jobs["sector"].fillna("").astype(str).str.lower().eq(selected_sector.lower())]
        only_seniority = jobs[jobs["seniority"].fillna("").astype(str).str.lower().eq(selected_seniority.lower())]
        if len(only_sector) >= len(only_seniority) and len(only_sector) > 0:
            messages.append(tr("jobs_fallback_seniority", seniority=selected_seniority))
            return only_sector, messages
        if len(only_seniority) > 0:
            messages.append(tr("jobs_fallback_sector", sector=selected_sector))
            return only_seniority, messages

        messages.append(tr("jobs_fallback_both", sector=selected_sector, seniority=selected_seniority))
        return jobs, messages

    if want_sector:
        out = jobs[jobs["sector"].fillna("").astype(str).str.lower().eq(selected_sector.lower())]
        if len(out) > 0:
            return out, messages
        messages.append(tr("jobs_fallback_sector", sector=selected_sector))
        return jobs, messages

    out = jobs[jobs["seniority"].fillna("").astype(str).str.lower().eq(selected_seniority.lower())]
    if len(out) > 0:
        return out, messages
    messages.append(tr("jobs_fallback_seniority", seniority=selected_seniority))
    return jobs, messages


def parse_docx_text(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            xml_data = zf.read("word/document.xml")
        root = ET.fromstring(xml_data)
        texts = [n.text for n in root.iter() if n.tag.endswith("}t") and n.text]
        return re.sub(r"\s+", " ", " ".join(texts)).strip()
    except Exception:
        return ""


@st.cache_data(show_spinner=False, ttl=1800)
def _cached_extract_pdf(file_bytes: bytes, suffix: str) -> str:
    """Cachea la extracción de texto del PDF por contenido (hash implícito en st.cache_data)."""
    if suffix == ".pdf":
        return _extract_pdf_from_bytes(file_bytes)
    if suffix == ".txt":
        try:
            return re.sub(r"\s+", " ", file_bytes.decode("utf-8", errors="ignore")).strip()
        except Exception:
            return ""
    if suffix == ".docx":
        return parse_docx_text(file_bytes)
    return ""


def read_uploaded_cv(uploaded_file, model_module) -> str:
    if uploaded_file is None:
        return ""

    file_bytes = uploaded_file.getvalue()
    if not file_bytes:
        return ""

    suffix = Path(uploaded_file.name or "").suffix.lower()
    # Usa la versión cacheada (mismo archivo → resultado instantáneo en reruns)
    text = _cached_extract_pdf(file_bytes, suffix)
    if text:
        return re.sub(r"\s+", " ", text).strip()

    # Fallback para PDFs que no extrajeron texto: lector del modelo
    if suffix == ".pdf":
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = Path(tmp.name)
            text = model_module.read_resume_pdf_text(tmp_path) or ""
            try:
                tmp_path.unlink()
            except Exception:
                pass
            return re.sub(r"\s+", " ", text).strip()
        except Exception:
            return ""
    return ""


def _extract_pdf_from_bytes(file_bytes: bytes) -> str:
    """Extract text from PDF bytes. Tries text parsers first, then OCR for scanned PDFs."""
    import io

    # 1. pypdf
    try:
        from pypdf import PdfReader
        parts = [p.extract_text() or "" for p in PdfReader(io.BytesIO(file_bytes)).pages]
        text = " ".join(parts).strip()
        if text:
            return text
    except Exception:
        pass

    # 2. pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            parts = [p.extract_text() or "" for p in pdf.pages]
        text = " ".join(parts).strip()
        if text:
            return text
    except Exception:
        pass

    # 3. fitz / PyMuPDF — text layer
    try:
        import fitz
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            parts = [page.get_text("text") or "" for page in doc]
        text = " ".join(parts).strip()
        if text:
            return text
    except Exception:
        pass

    # 4. OCR fallback for scanned/image-based PDFs
    #    Uses fitz to render pages as images, then pytesseract for OCR
    try:
        import fitz
        import pytesseract
        from PIL import Image

        ocr_parts = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom → better OCR accuracy
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = pytesseract.image_to_string(img, lang="spa+eng")
                if ocr_text.strip():
                    ocr_parts.append(ocr_text.strip())
        text = " ".join(ocr_parts).strip()
        if text:
            return text
    except Exception:
        pass

    # 5. OCR fallback via pdf2image + pytesseract (if fitz not available)
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=200)
        ocr_parts = [pytesseract.image_to_string(img, lang="spa+eng") for img in images]
        text = " ".join(ocr_parts).strip()
        if text:
            return text
    except Exception:
        pass

    return ""


def build_job_search_link(row: pd.Series) -> str:
    site = str(row.get("site", "")).strip().lower()
    title = str(row.get("title", "")).strip()
    location = str(row.get("location", "")).strip()
    if site == "linkedin":
        return f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(title)}&location={quote_plus(location)}"
    return f"https://www.indeed.com/jobs?q={quote_plus(title)}&l={quote_plus(location)}"


def normalize_course_url(url: str) -> str:
    txt = str(url or "").strip()
    if not txt:
        return ""
    if txt.startswith("http://") or txt.startswith("https://"):
        return txt
    if txt.startswith("/"):
        return "https://www.udemy.com" + txt
    return "https://" + txt


def format_course_price(row: pd.Series) -> str:
    pric_col = row.get("PRIC")
    if pd.notna(pric_col):
        txt = str(pric_col).strip()
        if txt and txt.upper() != "N/D":
            v = parse_price_token(txt)
            if v is not None and v >= 5:
                return txt
    # Prefer scraped cache prices when available.
    scraped_txt = row.get("price_text")
    if pd.notna(scraped_txt):
        txt = str(scraped_txt).strip()
        if txt and txt.upper() != "N/D":
            v = parse_price_token(txt)
            if v is not None and v >= 5:
                return txt
    for col in ["price_value_eur", "price_eur", "price", "tuition"]:
        if col in row and pd.notna(row.get(col)):
            val = row.get(col)
            if isinstance(val, (int, float)):
                if float(val) >= 5:
                    return format_price_eur(val)
                continue
            parsed = parse_price_token(val)
            if parsed is not None and parsed >= 5:
                return str(val)
    return "N/D"


def get_course_price_source(row: pd.Series) -> str:
    v = row.get("PRIC_SOURCE")
    if pd.notna(v):
        txt = str(v).strip()
        if txt and txt.lower() != "none":
            return txt
    v2 = row.get("price_source")
    if pd.notna(v2):
        txt2 = str(v2).strip()
        if txt2 and txt2.lower() != "none":
            return txt2
    return "none"


def _parse_price_from_json(data) -> str:
    if not isinstance(data, dict):
        return "N/D"
    candidates = [
        data.get("price"),
        data.get("list_price"),
        (data.get("price_detail") or {}).get("price_string"),
        (data.get("price_detail") or {}).get("amount"),
    ]
    for c in candidates:
        if c is None:
            continue
        txt = str(c).strip()
        if txt:
            return txt
    return "N/D"


def _extract_price_recursive(obj) -> str:
    if isinstance(obj, dict):
        if "price_string" in obj and obj["price_string"]:
            return str(obj["price_string"])
        if "amount" in obj and "currency" in obj:
            return f"{obj['amount']} {obj['currency']}"
        for v in obj.values():
            r = _extract_price_recursive(v)
            if r != "N/D":
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _extract_price_recursive(v)
            if r != "N/D":
                return r
    return "N/D"


def _clean_price_string(raw: str) -> str:
    if not raw:
        return "N/D"
    txt = html.unescape(str(raw))
    txt = txt.replace("\\u20ac", "EUR ").replace("\\u00a3", "GBP ").replace("\\u0024", "USD ")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt or "N/D"


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_live_course_price(url: str, course_id=None) -> str:
    clean_url = normalize_course_url(url)
    if not clean_url and course_id is None:
        return "N/D"

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/html;q=0.9,*/*;q=0.8"}

    # 1) Udemy API by course_id (if available in dataset).
    if course_id is not None:
        try:
            api_url = f"https://www.udemy.com/api-2.0/courses/{int(course_id)}/?fields[course]=price,price_detail,list_price"
            resp = requests.get(api_url, headers=headers, timeout=8)
            if resp.ok:
                price = _parse_price_from_json(resp.json())
                if price != "N/D":
                    return _clean_price_string(price)
        except Exception:
            pass
        try:
            comp_url = (
                f"https://www.udemy.com/api-2.0/course-landing-components/{int(course_id)}/me/"
                "?components=buy_button,deal_badge,price_text,discount_expiration"
            )
            resp2 = requests.get(comp_url, headers=headers, timeout=8)
            if resp2.ok:
                deep_price = _extract_price_recursive(resp2.json())
                if deep_price != "N/D":
                    return _clean_price_string(deep_price)
        except Exception:
            pass

    # 2) HTML page patterns.
    if not clean_url:
        return "N/D"
    try:
        html = requests.get(clean_url, headers=headers, timeout=8).text
    except Exception:
        return "N/D"

    patterns = [
        r'"discount_price"\s*:\s*"([^"]+)"',
        r'"price_string"\s*:\s*"([^"]+)"',
        r'"list_price"\s*:\s*"([^"]+)"',
        r'"amount"\s*:\s*"([^"]+)"',
        r'"priceText"\s*:\s*"([^"]+)"',
        r'"price"\s*:\s*"([^"]+)"',
        r'"discount_price"\s*:\s*\{[^}]*"price_string"\s*:\s*"([^"]+)"',
        r'"discount_price"\s*:\s*\{[^}]*"amount"\s*:\s*([0-9]+(?:\.[0-9]{1,2})?)',
        r'"priceCurrency"\s*:\s*"([A-Z]{3})"\s*,\s*"price"\s*:\s*"([0-9]+(?:\.[0-9]{1,2})?)"',
        r'product:price:amount"\s+content="([^"]+)"',
        r">\s*([€$£]\s?[0-9]+(?:[.,][0-9]{2})?)\s*</span>",
        r">\s*([€$£]\s?[0-9]+(?:[.,][0-9]{2})?)\s*</div>",
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            if m.lastindex and m.lastindex >= 2:
                val = f"{m.group(2).strip()} {m.group(1).strip()}"
            else:
                val = m.group(1).strip()
            if val:
                return _clean_price_string(val)

    generic = re.search(r"([€$£]\s?[0-9]+(?:[.,][0-9]{2})?)", html)
    if generic:
        return _clean_price_string(generic.group(1))
    return "N/D"


def build_skill_course_map(gap_skills: list[str], courses_feat: pd.DataFrame, course_skills: pd.DataFrame, max_courses: int = 3) -> dict:
    if not gap_skills:
        return {}
    cf = courses_feat.copy()
    cf["rating"] = pd.to_numeric(cf["rating"], errors="coerce")
    cf["num_reviews"] = pd.to_numeric(cf["num_reviews"], errors="coerce")
    cf["quality"] = cf["rating"].fillna(0.0) * cf["num_reviews"].fillna(0.0).map(lambda x: math.log1p(float(x)))

    map_df = course_skills.copy()
    map_df["skill"] = map_df["skill"].astype(str)
    map_df = map_df[map_df["skill"].isin(gap_skills)]
    if map_df.empty:
        return {}

    merged = map_df.merge(
        cf[["course_id", "title", "rating", "num_reviews", "duration", "url", "quality"]],
        on="course_id",
        how="left",
    )
    merged = merged.sort_values(["skill", "quality", "rating", "num_reviews"], ascending=[True, False, False, False])

    out = {}
    for skill in gap_skills:
        chunk = merged[merged["skill"] == skill].drop_duplicates(subset=["course_id"]).head(max_courses)
        out[skill] = chunk.to_dict("records")
    return out


def prioritize_gap_skills(
    gap_skills: list[str],
    role_skill_demand: pd.DataFrame,
    target_role: str,
    max_skills: int = 3,
) -> list[str]:
    if not gap_skills:
        return []
    if role_skill_demand is None or role_skill_demand.empty:
        return list(gap_skills[:max_skills])

    demand = role_skill_demand.copy()
    demand.columns = [str(c).strip() for c in demand.columns]
    role_col = "role_family" if "role_family" in demand.columns else next((c for c in demand.columns if "role" in c.lower()), None)
    skill_col = "skill" if "skill" in demand.columns else next((c for c in demand.columns if "skill" in c.lower()), None)
    if not role_col or not skill_col:
        return list(gap_skills[:max_skills])

    demand[role_col] = demand[role_col].astype(str).str.strip().str.lower()
    demand[skill_col] = demand[skill_col].astype(str).str.strip().str.lower()
    demand = demand[demand[role_col] == str(target_role or "").strip().lower()].copy()

    gap_norm = [str(s or "").strip().lower() for s in gap_skills if str(s or "").strip()]
    if demand.empty:
        return gap_norm[:max_skills]

    score_rows = []
    for skill in gap_norm:
        chunk = demand[demand[skill_col] == skill]
        if chunk.empty:
            score_rows.append((skill, 0.0, 0.0))
            continue
        demand_ratio = float(pd.to_numeric(chunk.get("demand_ratio"), errors="coerce").fillna(0.0).max()) if "demand_ratio" in chunk.columns else 0.0
        demand_count = float(pd.to_numeric(chunk.get("demand_count"), errors="coerce").fillna(0.0).max()) if "demand_count" in chunk.columns else 0.0
        score_rows.append((skill, demand_ratio, demand_count))

    score_rows = sorted(score_rows, key=lambda x: (-x[1], -x[2], gap_norm.index(x[0])))
    return [skill for skill, _, _ in score_rows[:max_skills]]


def build_goal_top_courses(
    ranked_courses: pd.DataFrame,
    priority_gap_skills: list[str],
    courses_feat: pd.DataFrame,
    course_skills: pd.DataFrame,
    max_courses: int = 3,
) -> pd.DataFrame:
    if ranked_courses is None or ranked_courses.empty:
        return ranked_courses
    if not priority_gap_skills:
        return ranked_courses.head(max_courses).copy()

    skill_map = build_skill_course_map(priority_gap_skills, courses_feat, course_skills, max_courses=max_courses)
    ranked_view = ranked_courses.copy()
    ranked_view["course_id"] = ranked_view["course_id"].astype(str)
    chosen_ids: list[str] = []
    chosen_rows: list[pd.Series] = []

    for skill in priority_gap_skills:
        candidates = skill_map.get(skill, []) or []
        for cand in candidates:
            cid = str(cand.get("course_id", "")).strip()
            if not cid or cid in chosen_ids:
                continue
            match = ranked_view[ranked_view["course_id"] == cid]
            if match.empty:
                continue
            chosen_ids.append(cid)
            chosen_rows.append(match.iloc[0])
            break

    if len(chosen_rows) < max_courses:
        for _, row in ranked_view.iterrows():
            cid = str(row.get("course_id", "")).strip()
            if cid and cid not in chosen_ids:
                chosen_ids.append(cid)
                chosen_rows.append(row)
            if len(chosen_rows) >= max_courses:
                break

    if not chosen_rows:
        return ranked_view.head(max_courses).copy()
    return pd.DataFrame(chosen_rows).head(max_courses).copy()


def render_skill_chips(
    skills: list[str],
    variant: str = "neutral",
    max_items: int = 12,
    state_key: str | None = None,
):
    if not skills:
        render_result_notice(tr("no_skills_detected"), tone="info")
        return
    expanded = True
    if state_key:
        expanded = bool(st.session_state.get(state_key, False))
    shown = skills if expanded else skills[:max_items]
    chips = "".join(render_skill_tag(humanize_label(skill), variant=variant) for skill in shown)
    st.markdown(f"<div class='chips-wrap'>{chips}</div>", unsafe_allow_html=True)
    if state_key and len(skills) > max_items:
        label = tr("show_less") if expanded else tr("view_more")
        if st.button(label, key=f"btn_{state_key}"):
            st.session_state[state_key] = not expanded
            st.rerun()


def render_result_notice(message: str, tone: str = "info"):
    tone_key = str(tone or "info").strip().lower()
    palette = {
        "success": {
            "bg": "rgba(10,240,200,0.08)",
            "border": "rgba(10,240,200,0.24)",
            "accent": "#0AF0C8",
        },
        "error": {
            "bg": "rgba(255,77,106,0.08)",
            "border": "rgba(255,77,106,0.24)",
            "accent": "#FF4D6A",
        },
        "warning": {
            "bg": "rgba(255,183,77,0.10)",
            "border": "rgba(255,183,77,0.28)",
            "accent": "#FFB74D",
        },
        "info": {
            "bg": "rgba(61,110,255,0.06)",
            "border": "rgba(61,110,255,0.20)",
            "accent": "#6B9AFF",
        },
    }
    colors = palette.get(tone_key, palette["info"])
    style_parts = [
        f"background:{colors['bg']}",
        f"border:1px solid {colors['border']}",
        "border-radius:10px",
        "padding:16px 20px",
        "margin:12px 0",
        "color:#ffffff",
        "-webkit-text-fill-color:#ffffff",
        "font-size:14px",
        "line-height:1.7",
    ]
    if tone_key == "info":
        style_parts.insert(2, f"border-left:3px solid {colors['accent']}")
    style_attr = ";".join(style_parts) + ";"
    msg = escape(str(message))
    html = (
        f'<div style="{style_attr}">'
        f'<span style="color:#ffffff;-webkit-text-fill-color:#ffffff;">✦ {msg}</span>'
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_role_fit_notice(rec: dict, target_role: str, role_label: str):
    best_role = str(rec.get("detected_best_role", "") or "")
    best_score = int(rec.get("detected_best_role_score", 0) or 0)
    target_score = int(round(float(rec.get("role_match_score_current", 0.0) or 0.0)))
    score_after  = int(round(float(rec.get("role_match_score_after_path", 0.0) or 0.0)))
    lang = st.session_state.get("lang", "es")
    role_labels = {
        "es": {
            "ml_engineer": "Machine Learning Engineer",
            "data_scientist": "Data Scientist",
            "data_engineer": "Data Engineer",
            "data_analyst": "Data Analyst",
            "other_data_role": "Otro rol de datos",
        },
        "en": {
            "ml_engineer": "Machine Learning Engineer",
            "data_scientist": "Data Scientist",
            "data_engineer": "Data Engineer",
            "data_analyst": "Data Analyst",
            "other_data_role": "Other Data Role",
        },
    }
    best_label = role_labels.get(lang, role_labels["en"]).get(best_role, best_role)

    has_better_role = (
        best_role
        and best_role != target_role
        and best_score > target_score + 10
        and best_score > 20
    )

    # Badge principal: siempre visible — compatibilidad actual con el rol objetivo
    # No mostramos el score "después de la ruta" porque incluye experiencia laboral
    # que un curso no puede sustituir; se vería artificialmente bajo y confundiría al usuario.
    label_now    = "Compatibilidad actual" if lang == "es" else "Current match"
    label_role   = "Rol objetivo" if lang == "es" else "Target role"
    skill_gain   = max(0, score_after - target_score)
    label_gain   = (f"La ruta mejora tu perfil +{skill_gain} puntos" if lang == "es"
                    else f"The path improves your profile +{skill_gain} points")

    score_color = "#0AF0C8" if target_score >= 60 else ("#F59E0B" if target_score >= 35 else "#FF6B85")

    gain_block = ""
    if skill_gain > 0:
        gain_block = (
            f'<div style="font-size:12px;color:rgba(255,255,255,0.45);margin-top:6px;">'
            f'<span style="color:#0AF0C8;font-weight:700;">↑ +{skill_gain}%</span>'
            f'&nbsp;{"con la ruta propuesta" if lang == "es" else "with the proposed path"}'
            f'</div>'
        )

    main_badge = f"""
    <div style="
      display:flex;align-items:stretch;gap:12px;
      background:rgba(10,240,200,0.04);
      border:1px solid rgba(10,240,200,0.15);
      border-radius:12px;padding:16px 20px;margin:12px 0 8px;
    ">
      <div style="flex:0 0 auto;display:flex;flex-direction:column;justify-content:center;
        align-items:center;padding-right:16px;border-right:1px solid rgba(255,255,255,0.08);">
        <div style="font-size:32px;font-weight:800;color:{score_color};
          letter-spacing:-0.02em;line-height:1;">{target_score}%</div>
        <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:0.1em;
          margin-top:4px;text-align:center;">{label_now}</div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding-left:4px;">
        <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;
          color:rgba(255,255,255,0.35);margin-bottom:4px;">{label_role}</div>
        <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:2px;">
          {escape(role_label)}
        </div>
        {gain_block}
      </div>
    </div>"""

    st.markdown(main_badge, unsafe_allow_html=True)

    # Bloque adicional: solo si hay un rol que encaja mejor actualmente
    if has_better_role:
        if lang == "es":
            candidate_name = st.session_state.get("caiq_candidate_name", "")
            first_name = candidate_name.split()[0] if candidate_name else ""
            greeting = f"{first_name}, tu" if first_name else "Tu"
            line1 = f"{greeting} perfil actual encaja algo mejor con <strong style='color:#0AF0C8;'>{escape(best_label)} ({best_score}%)</strong>. Si quieres un camino más corto, considera ese rol primero. O sigue con <strong style='color:rgba(255,255,255,0.8);'>{escape(role_label)}</strong> — la ruta te llevará ahí."
        else:
            candidate_name = st.session_state.get("caiq_candidate_name", "")
            first_name = candidate_name.split()[0] if candidate_name else ""
            greeting = f"{first_name}, your" if first_name else "Your"
            line1 = f"{greeting} current profile fits slightly better with <strong style='color:#0AF0C8;'>{escape(best_label)} ({best_score}%)</strong>. For a shorter path, consider that role first. Or continue with <strong style='color:rgba(255,255,255,0.8);'>{escape(role_label)}</strong> — the path will take you there."

        st.markdown(f"""
        <div style="
          background:rgba(61,110,255,0.05);
          border:1px solid rgba(61,110,255,0.18);
          border-left:3px solid #6B9AFF;
          border-radius:10px;padding:14px 18px;margin:4px 0 12px;
          font-size:13px;color:rgba(255,255,255,0.6);line-height:1.6;
        ">
          <span style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;
            color:rgba(255,255,255,0.3);display:block;margin-bottom:6px;">
            {"💡 Rol alternativo detectado" if lang == "es" else "💡 Alternative role detected"}
          </span>
          {line1}
        </div>
        """, unsafe_allow_html=True)


def render_pdf_export_button(
    rec: dict,
    candidate_profile: dict,
    candidate_skills_explicit: set,
    role_label: str,
    target_role: str,
):
    """Genera el informe PDF server-side con PyMuPDF y ofrece st.download_button."""
    import fitz  # PyMuPDF - ya en requirements.txt
    import io
    from datetime import date

    lang = st.session_state.get("lang", "es")

    # --- Datos del informe ---
    gap_set        = set(rec.get("gap_skills", []))
    remaining      = set(rec.get("remaining_gap", []))
    covered        = sorted(gap_set - remaining)
    core_gap       = list(rec.get("missing_core_skills", []) or [])
    important_gap  = list(rec.get("missing_important_skills", []) or [])
    all_gap        = list(rec.get("gap_skills", []) or [])
    priority_gap   = core_gap + [s for s in important_gap if s not in core_gap] + [
        s for s in all_gap if s not in core_gap and s not in important_gap
    ]
    detected_role  = str(candidate_profile.get("detected_best_role", "") or "")
    role_scores    = rec.get("role_scores_all", {}) or {}
    skills_n       = len(candidate_skills_explicit)
    gap_n          = len(rec.get("gap_skills", []))
    remaining_n    = len(rec.get("remaining_gap", []))
    covered_n      = gap_n - remaining_n
    pct            = round(covered_n / gap_n * 100) if gap_n > 0 else 0
    candidate_name = st.session_state.get("caiq_candidate_name", "")
    today          = date.today().strftime("%d/%m/%Y" if lang == "es" else "%m/%d/%Y")
    btn_label      = "⬇ Descargar informe PDF" if lang == "es" else "⬇ Download PDF report"
    safe_name      = candidate_name.replace(" ", "_") if candidate_name else "Informe"
    filename       = (
        f"CAIQ_Informe_{safe_name}.pdf" if lang == "es"
        else f"CAIQ_Report_{safe_name}.pdf"
    )

    role_display = {
        "ml_engineer":        "ML Engineer",
        "data_scientist":     "Data Scientist",
        "data_engineer":      "Data Engineer",
        "data_analyst":       "Data Analyst",
        "business_intelligence": "Business Intelligence",
        "mlops":              "MLOps",
        "other_data_role":    "Otro Rol de Datos" if lang == "es" else "Other Data Role",
    }

    # --- Colores (RGB 0-1) ---
    C_BG   = (0.059, 0.090, 0.161)   # #0F172A
    C_CARD = (0.118, 0.165, 0.239)   # #1E293B
    C_TEAL = (0.039, 0.941, 0.784)   # #0AF0C8
    C_WHITE= (1.0,   1.0,   1.0  )
    C_GRAY = (0.576, 0.635, 0.690)   # #94A3B8
    C_RED  = (1.0,   0.420, 0.522)   # #FF6B85
    C_BLUE = (0.420, 0.604, 1.0  )   # #6B9AFF

    W, H = 595, 842   # A4 puntos
    M = 36            # margen lateral

    doc  = fitz.open()
    page = doc.new_page(width=W, height=H)

    def rect(x0, y0, x1, y1):
        return fitz.Rect(x0, y0, x1, y1)

    def txt(point_or_x, y_or_text, text_or_size, size_or_color=10, color_or_fn=C_WHITE, fn="helv"):
        """Inserta texto. Acepta (x, y, text, size, color) o ((x,y), text, size, color)."""
        if isinstance(point_or_x, (list, tuple)) and not isinstance(point_or_x, fitz.Point):
            x, y = point_or_x
        elif isinstance(point_or_x, fitz.Point):
            x, y = point_or_x.x, point_or_x.y
        else:
            x = point_or_x
            y = y_or_text
            text_or_size, size_or_color, color_or_fn, fn = text_or_size, size_or_color, color_or_fn, fn
            y_or_text = text_or_size = text_or_size  # reassign below
        # Simplified: always (x, y, text, size, color, fontname)
        page.insert_text(fitz.Point(x, y), str(y_or_text),
                         fontsize=text_or_size, color=size_or_color,
                         fontname=color_or_fn)

    def draw_bg():
        page.draw_rect(rect(0, 0, W, H), color=C_BG, fill=C_BG)

    def draw_header(y):
        # Wordmark
        page.insert_text(fitz.Point(M, y + 26), "CAIQ", fontsize=24, color=C_WHITE, fontname="hebo")
        page.insert_text(fitz.Point(M + 64, y + 26), "  Career Alignment and Insight Qualifier",
                         fontsize=9, color=C_GRAY, fontname="helv")
        # Fecha y nombre arriba derecha
        right_x = W - M - 130
        page.insert_text(fitz.Point(right_x, y + 14), today, fontsize=8, color=C_GRAY, fontname="helv")
        if candidate_name:
            page.insert_text(fitz.Point(right_x, y + 28), candidate_name[:28],
                             fontsize=10, color=C_WHITE, fontname="helv")
        # Línea teal
        yline = y + 38
        page.draw_line(fitz.Point(M, yline), fitz.Point(W - M, yline), color=C_TEAL, width=1.5)
        return yline + 14

    def draw_section_label(y, label, color=C_TEAL):
        page.insert_text(fitz.Point(M, y), label.upper(), fontsize=7, color=color, fontname="helv")
        return y + 12

    def draw_progress_bar(y, pct_val, color=C_TEAL):
        bh = 7
        page.draw_rect(rect(M, y, W - M, y + bh), color=C_CARD, fill=C_CARD)
        fill_w = max(4, int((W - 2 * M) * pct_val / 100))
        page.draw_rect(rect(M, y, M + fill_w, y + bh), color=color, fill=color)
        return y + bh + 4

    def draw_card_row(y, items_2col):
        """items_2col: lista de (label, value) pares, máx 4, en 2 columnas."""
        col_w = (W - 2 * M - 8) / 2
        ch = 38
        for idx, (lbl, val) in enumerate(items_2col[:4]):
            cx = M + (idx % 2) * (col_w + 8)
            cy = y + (idx // 2) * (ch + 6)
            page.draw_rect(rect(cx, cy, cx + col_w, cy + ch), color=C_CARD, fill=C_CARD)
            page.insert_text(fitz.Point(cx + 8, cy + 12), str(lbl),
                             fontsize=7, color=C_GRAY, fontname="helv")
            page.insert_text(fitz.Point(cx + 8, cy + 28), str(val)[:30],
                             fontsize=11, color=C_WHITE, fontname="helv")
        rows = (len(items_2col[:4]) + 1) // 2
        return y + rows * (ch + 6) + 4

    def draw_role_bars(y):
        for role, score in sorted(role_scores.items(), key=lambda x: -x[1]):
            if role == "other_data_role":
                continue
            lbl = role_display.get(role, role)
            is_target = role == target_role
            bar_color = C_TEAL if is_target else C_BLUE
            sc = int(score)
            # Label + %
            page.insert_text(fitz.Point(M, y + 9),
                             lbl + (" ← objetivo" if (is_target and lang == "es") else (" ← goal" if is_target else "")),
                             fontsize=8, color=C_WHITE if is_target else C_GRAY, fontname="helv")
            page.insert_text(fitz.Point(W - M - 32, y + 9), f"{sc}%",
                             fontsize=8, color=bar_color, fontname="helv")
            y = draw_progress_bar(y + 11, sc, bar_color)
            y += 2
        return y + 4

    def draw_skills_row(y, title_str, skills_list, color):
        if not skills_list:
            return y
        y = draw_section_label(y, title_str, color)
        chips = "  ·  ".join(humanize_label(s) for s in skills_list[:14])
        tb = rect(M, y, W - M, y + 36)
        page.insert_textbox(tb, chips, fontsize=8, color=color, fontname="helv", align=0)
        return y + 28

    def draw_footer(y):
        page.draw_line(fitz.Point(M, y), fitz.Point(W - M, y), color=C_CARD, width=0.8)
        page.insert_text(fitz.Point(M, y + 12),
                         f"CAIQ · caiq.app · {today}",
                         fontsize=7, color=C_GRAY, fontname="helv")

    # --- Componer página ---
    draw_bg()
    y = 28
    y = draw_header(y)

    # Tarjetas de perfil
    detected_label = humanize_label(detected_role) if detected_role else role_label
    profile_items = [
        ("Perfil detectado" if lang == "es" else "Detected profile", detected_label[:24]),
        ("Rol objetivo"     if lang == "es" else "Target role",       role_label[:24]),
        ("Skills en CV"     if lang == "es" else "Skills in CV",      str(skills_n)),
        ("Gap de skills"    if lang == "es" else "Skills gap",        str(gap_n)),
    ]
    y = draw_card_row(y, profile_items)
    y += 4

    # Barra de cobertura de la ruta
    cov_label = (
        f"Compatibilidad con el rol objetivo tras la ruta: {pct}%"
        if lang == "es"
        else f"Role fit after completing the path: {pct}%"
    )
    page.insert_text(fitz.Point(M, y), cov_label, fontsize=8, color=C_GRAY, fontname="helv")
    y += 10
    y = draw_progress_bar(y, pct)
    y += 6

    # Compatibilidad por rol
    y = draw_section_label(y, "Compatibilidad por rol" if lang == "es" else "Role compatibility")
    y = draw_role_bars(y)

    # Skills
    y = draw_skills_row(y, "Skills detectadas" if lang == "es" else "Detected skills",
                        sorted(candidate_skills_explicit), C_TEAL)
    y = draw_skills_row(y, "Skills en falta"   if lang == "es" else "Missing skills",
                        priority_gap, C_RED)
    y = draw_skills_row(y, "Cubre la ruta"     if lang == "es" else "Path covers",
                        covered, C_BLUE)

    draw_footer(H - 26)

    # --- Serializar y ofrecer descarga ---
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)

    st.download_button(
        label=btn_label,
        data=buf.getvalue(),
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
    )



def render_loading_screen():
    st.markdown(f"""
    <style>
    @keyframes spin {{
        to {{ stroke-dashoffset: -60; }}
    }}
    @keyframes bar {{
        0%   {{ width: 0%; }}
        100% {{ width: 100%; }}
    }}
    .caiq-loader {{
        background: #060E1E;
        border: 1px solid rgba(10,240,200,0.12);
        border-radius: 16px;
        padding: 40px 32px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
        text-align: center;
        max-width: 420px;
        width: min(420px, 92vw);
        margin: 0 auto;
        box-shadow: 0 20px 50px rgba(0,0,0,0.45);
    }}
    .caiq-loader-overlay {{
        position: fixed;
        inset: 0;
        background: rgba(3,8,17,0.58);
        backdrop-filter: blur(2px);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
    }}
    .caiq-loader-badge {{
        font-size: 10px;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: rgba(10,240,200,0.6);
        border: 1px solid rgba(10,240,200,0.18);
        padding: 4px 14px;
        border-radius: 100px;
    }}
    .caiq-loader-title {{
        font-size: 16px;
        font-weight: 600;
        color: #ffffff;
        line-height: 1.5;
        margin: 0;
    }}
    .caiq-loader-sub {{
        font-size: 13px;
        color: rgba(255,255,255,0.35);
        line-height: 1.6;
        margin: 0;
    }}
    .caiq-bar-track {{
        width: 100%;
        height: 3px;
        background: rgba(255,255,255,0.07);
        border-radius: 2px;
        overflow: hidden;
    }}
    .caiq-bar-fill {{
        height: 100%;
        background: linear-gradient(90deg, #0AF0C8 0%, #38bdf8 60%, #0AF0C8 100%);
        background-size: 200% 100%;
        border-radius: 2px;
        animation: bar 2.2s ease-in-out infinite alternate, shimmer 1.8s linear infinite;
    }}
    @keyframes shimmer {{
        0% {{ background-position: 200% 0; }}
        100% {{ background-position: -200% 0; }}
    }}
    .caiq-spinner circle.track {{
        fill: none;
        stroke: rgba(10,240,200,0.1);
        stroke-width: 3;
    }}
    .caiq-spinner circle.arc {{
        fill: none;
        stroke: #0AF0C8;
        stroke-width: 3;
        stroke-dasharray: 40 60;
        stroke-linecap: round;
        animation: spin 1.2s linear infinite;
        transform-origin: 28px 28px;
    }}
    </style>

    <div class="caiq-loader-overlay">
        <div class="caiq-loader">
            <div class="caiq-loader-badge">CAIQ</div>
            <svg class="caiq-spinner" width="56" height="56" viewBox="0 0 56 56">
                <circle class="track" cx="28" cy="28" r="22"/>
                <circle class="arc"   cx="28" cy="28" r="22" stroke-dashoffset="0"/>
            </svg>
            <p class="caiq-loader-title">{tr('loading_title')}</p>
            <div class="caiq-bar-track">
                <div class="caiq-bar-fill"></div>
            </div>
            <p class="caiq-loader-sub">{tr('loading_sub')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_result_h3(title: str):
    st.markdown(
        (
            '<div class="caiq-result-title" style="color:#ffffff !important;font-size:24px;font-weight:700;'
            'letter-spacing:-0.02em;margin:24px 0 12px;'
            'background:transparent !important;-webkit-text-fill-color:#ffffff !important;">'
            f'<span style="color:#ffffff !important;-webkit-text-fill-color:#ffffff !important;">{escape(str(title))}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def clamp01(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def parse_duration_hours(duration_value) -> float | None:
    txt = str(duration_value or "").strip().lower()
    if not txt:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", txt)
    if not m:
        return None
    hours = float(m.group(1).replace(",", "."))
    if "min" in txt:
        return hours / 60.0
    return hours


def adaptive_weighted_score(parts: dict[str, float | None], weights: dict[str, float]) -> float:
    num = 0.0
    den = 0.0
    for key, value in parts.items():
        if value is None:
            continue
        w = float(weights.get(key, 0.0))
        if w <= 0:
            continue
        num += clamp01(value) * w
        den += w
    if den <= 0:
        return 0.0
    return num / den


def role_terms(target_role: str) -> list[str]:
    txt = humanize_label(target_role).lower()
    terms = [t for t in re.split(r"[^a-z0-9]+", txt) if len(t) > 2]
    return terms


def text_role_overlap_score(text_value: str, target_role: str) -> float | None:
    terms = role_terms(target_role)
    if not terms:
        return None
    txt = str(text_value or "").lower()
    if not txt.strip():
        return None
    hit = sum(1 for t in terms if t in txt)
    return clamp01(hit / len(terms))


def quality_signal(row: pd.Series) -> float | None:
    rating = pd.to_numeric(row.get("rating"), errors="coerce")
    reviews = pd.to_numeric(row.get("num_reviews"), errors="coerce")
    parts = []
    if pd.notna(rating):
        parts.append(clamp01(float(rating) / 5.0))
    if pd.notna(reviews):
        parts.append(clamp01(math.log1p(float(reviews)) / math.log1p(100000.0)))
    if not parts:
        return None
    return sum(parts) / len(parts)


def efficiency_signal(row: pd.Series, reco_type: str, price_txt: str | None = None) -> float | None:
    signals = []
    if reco_type == "course":
        hours = parse_duration_hours(row.get("duration"))
        if hours is not None:
            signals.append(clamp01(1.0 - min(hours, 80.0) / 80.0))
        price_raw = price_txt if price_txt is not None else format_course_price(row)
        price_val = parse_price_token(price_raw)
        if price_val is not None and price_val >= 5:
            signals.append(clamp01(1.0 - min(float(price_val), 250.0) / 250.0))
    elif reco_type == "master":
        master_price = normalize_master_price_value(row.get("price_value_eur"), row.get("tuition"))
        if master_price is not None and master_price >= 500:
            signals.append(clamp01(1.0 - min(float(master_price), 45000.0) / 45000.0))
    if not signals:
        return None
    return sum(signals) / len(signals)


RANKING_BADGE_CONFIG = {
    "rank_top": {"label_key": "badge_rank_top", "tip_key": "badge_rank_top_tip", "css": "impact"},
    "rank_balanced": {"label_key": "badge_rank_balanced", "tip_key": "badge_rank_balanced_tip", "css": "balanced"},
    "rank_fast": {"label_key": "badge_rank_fast", "tip_key": "badge_rank_fast_tip", "css": "fast"},
    "rank_complete": {"label_key": "badge_rank_complete", "tip_key": "badge_rank_complete_tip", "css": "complete"},
    "rank_job_top": {"label_key": "badge_rank_job_top", "tip_key": "badge_rank_job_top_tip", "css": "impact"},
    "rank_job_solid": {"label_key": "badge_rank_job_solid", "tip_key": "badge_rank_job_solid_tip", "css": "balanced"},
    "rank_job_aspirational": {"label_key": "badge_rank_job_aspirational", "tip_key": "badge_rank_job_aspirational_tip", "css": "fast"},
}


def get_metric_labels_by_type(item_type: str) -> dict[str, str]:
    if item_type in {"course", "master"}:
        return {
            "coverage": tr("coverage_component"),
        }
    return {
        "profile_match": tr("job_match_profile"),
    }


def get_role_orientation_label(score_01: float) -> str:
    s = clamp01(score_01)
    if s >= 0.66:
        return tr("role_orientation_high")
    if s >= 0.40:
        return tr("role_orientation_medium")
    return tr("role_orientation_low")


def get_role_orientation_level(score_01: float, low_thr: float = 0.40, high_thr: float = 0.66) -> str:
    s = clamp01(score_01)
    if s >= high_thr:
        return "high"
    if s >= low_thr:
        return "medium"
    return "low"


def get_training_category(meta: dict) -> dict:
    cov = int(meta.get("coverage_pct", 0))
    orient = str(meta.get("orientation_level", "low"))
    quality = int(meta.get("quality_pct", 0)) if meta.get("quality_pct") is not None else 0
    efficiency = int(meta.get("efficiency_pct", 0)) if meta.get("efficiency_pct") is not None else 0

    if cov >= 82 and orient == "high":
        return {"label": tr("label_direct_role"), "text": tr("insight_direct_role"), "css": "strategy-direct"}
    if orient == "high" and cov < 74:
        return {"label": tr("label_specialized"), "text": tr("insight_specialized"), "css": "strategy-comp"}
    if cov >= 76 and orient in {"medium", "high"}:
        return {"label": tr("label_base_technical"), "text": tr("insight_base_technical"), "css": "strategy-fast"}
    if cov >= 64 and orient in {"low", "medium"} and (quality < 80 and efficiency < 75):
        return {"label": tr("label_close_gaps"), "text": tr("insight_close_gaps"), "css": "strategy-gap"}
    if orient == "medium" and (quality >= 80 or efficiency >= 75):
        return {"label": tr("label_specialized"), "text": tr("insight_specialized"), "css": "strategy-comp"}
    if cov >= 48 or quality >= 65 or efficiency >= 65:
        return {"label": tr("label_complementary"), "text": tr("insight_complementary"), "css": "strategy-comp"}
    return {"label": tr("label_low_priority"), "text": tr("insight_low_priority"), "css": "strategy-low"}


def stable_variant_idx(seed_text: str, n: int) -> int:
    if n <= 1:
        return 0
    seed = str(seed_text or "")
    return sum(ord(ch) for ch in seed) % n


def calibrate_training_orientation_levels(rows: list[dict]) -> list[dict]:
    if not rows:
        return rows
    vals = [clamp01(float(it.get("meta", {}).get("alignment_score", 0.0))) for it in rows]
    n = len(vals)
    ordered_idx = sorted(range(n), key=lambda i: vals[i], reverse=True)

    # Relative buckets for comparability inside each recommendation set.
    hi_cut = max(1, int(math.ceil(n * 0.28)))
    mid_cut = max(hi_cut + 1, int(math.ceil(n * 0.68)))
    for rank, idx in enumerate(ordered_idx):
        s = vals[idx]
        if rank < hi_cut and s >= 0.46:
            lvl = "high"
        elif rank < mid_cut and s >= 0.32:
            lvl = "medium"
        else:
            lvl = "low"
        rows[idx]["meta"]["orientation_level"] = lvl

    # Credibility guardrails (never inflate extremely low scores).
    for idx in ordered_idx:
        s = vals[idx]
        lvl = rows[idx]["meta"].get("orientation_level", "low")
        if s < 0.25:
            rows[idx]["meta"]["orientation_level"] = "low"
        elif s < 0.35 and lvl == "high":
            rows[idx]["meta"]["orientation_level"] = "medium"

    # Ensure at least one medium when list has enough options and spread is non-trivial.
    if n >= 4:
        levels_now = [rows[i]["meta"].get("orientation_level", "low") for i in range(n)]
        if "medium" not in levels_now:
            rows[ordered_idx[min(1, n - 1)]]["meta"]["orientation_level"] = "medium"

    for it in rows:
        lvl = str(it.get("meta", {}).get("orientation_level", "low"))
        if lvl == "high":
            it["meta"]["orientation_label"] = tr("role_orientation_high")
        elif lvl == "medium":
            it["meta"]["orientation_label"] = tr("role_orientation_medium")
        else:
            it["meta"]["orientation_label"] = tr("role_orientation_low")
    return rows


def get_interpretation_badge(item_type: str, coverage_pct: int, closeness_pct: int, score_pct: int) -> dict:
    if item_type in {"course", "master"}:
        if coverage_pct >= 82 and closeness_pct >= 70:
            return {
                "label": tr("label_direct_role"),
                "text": tr("insight_direct_role"),
                "css": "strategy-direct",
            }
        if closeness_pct >= 72 and coverage_pct < 72:
            return {
                "label": tr("label_specialized"),
                "text": tr("insight_specialized"),
                "css": "strategy-comp",
            }
        if coverage_pct >= 80 and closeness_pct >= 45:
            return {
                "label": tr("label_base_technical"),
                "text": tr("insight_base_technical"),
                "css": "strategy-fast",
            }
        if coverage_pct >= 62 and closeness_pct < 72:
            return {
                "label": tr("label_close_gaps"),
                "text": tr("insight_close_gaps"),
                "css": "strategy-gap",
            }
        if coverage_pct >= 48 and closeness_pct >= 45:
            return {
                "label": tr("label_complementary"),
                "text": tr("insight_complementary"),
                "css": "strategy-comp",
            }
        return {
            "label": tr("label_low_priority"),
            "text": tr("insight_low_priority"),
            "css": "strategy-low",
        }

    if score_pct >= 88:
        return {"label": tr("job_label_strong_fit"), "text": tr("job_insight_strong_fit"), "css": "strategy-direct"}
    if score_pct >= 74:
        return {"label": tr("job_label_good_fit"), "text": tr("job_insight_good_fit"), "css": "strategy-comp"}
    if score_pct >= 58:
        return {"label": tr("job_label_partial_fit"), "text": tr("job_insight_partial_fit"), "css": "strategy-gap"}
    return {"label": tr("job_label_aspirational"), "text": tr("job_insight_aspirational"), "css": "strategy-low"}


def get_explanation_text(item_type: str, badge_payload: dict, meta: dict, row: pd.Series) -> str:
    base = str(badge_payload.get("text", "")).strip()
    if not base:
        return ""

    if item_type in {"course", "master"}:
        hints = []
        if item_type == "course":
            hrs = parse_duration_hours(row.get("duration"))
            if hrs is not None and hrs <= 8:
                hints.append("Formato ágil para avanzar en poco tiempo.")
            rating = pd.to_numeric(row.get("rating"), errors="coerce")
            if pd.notna(rating) and float(rating) >= 4.6:
                hints.append("Cuenta con valoración alta de alumnos.")
            price_val = parse_price_token(format_course_price(row))
            if price_val is not None and price_val <= 35:
                hints.append("Coste contenido para empezar sin gran inversión.")
        else:
            mprice = normalize_master_price_value(row.get("price_value_eur"), row.get("tuition"))
            if mprice is not None and mprice <= 8000:
                hints.append("Buena relación entre enfoque y coste para este tipo de programa.")
            if "online" in str(row.get("location", "")).lower():
                hints.append("Modalidad flexible para compatibilizar aprendizaje y trabajo.")

        orient = str(meta.get("orientation_level", ""))
        if orient == "high":
            hints.append("Orientación al rol alta dentro del conjunto recomendado.")
        elif orient == "medium":
            hints.append("Orientación al rol equilibrada para combinar progreso y foco.")

        variants = [base] + [f"{base} {h}" for h in hints]
        return variants[stable_variant_idx(str(row.get('title', row.get('program_name', ''))), len(variants))]

    match = int(meta.get("score_pct", 0))
    job_hints = []
    if match >= 85:
        job_hints.append("Candidatura realista a corto plazo.")
    elif match >= 70:
        job_hints.append("Buena opción para aplicar con criterio.")
    elif match >= 55:
        job_hints.append("Requiere cubrir algunos requisitos para competir con más fuerza.")
    else:
        job_hints.append("Enfoque aspiracional, recomendable como objetivo de evolución.")
    if str(row.get("seniority", "")).strip():
        job_hints.append(f"Nivel solicitado: {str(row.get('seniority')).strip()}.")
    if str(row.get("location", "")).strip():
        job_hints.append(f"Ubicación: {str(row.get('location')).strip()}.")
    mode_txt = str(row.get("work_mode", row.get("work_type", ""))).strip()
    if mode_txt:
        job_hints.append(f"Modalidad: {mode_txt}.")
    variants = [base] + [f"{base} {h}" for h in job_hints]
    seed = f"{row.get('title','')}|{row.get('company','')}|{row.get('location','')}"
    return variants[stable_variant_idx(seed, len(variants))]


def get_display_metrics(item_type: str, meta: dict) -> list[str]:
    labels = get_metric_labels_by_type(item_type)
    if item_type in {"course", "master"}:
        return [labels["coverage"].format(value=int(meta.get("coverage_pct", 0)))]
    return []


def get_ranking_badge(item_type: str, position: int) -> str | None:
    if item_type == "job":
        if position == 0:
            return "rank_job_top"
        if position == 1:
            return "rank_job_solid"
        if position == 2:
            return "rank_job_aspirational"
        return None
    if position == 0:
        return "rank_top"
    if position == 1:
        return "rank_balanced"
    if position == 2:
        return "rank_fast" if item_type == "course" else "rank_complete"
    return None


def assign_ranking_badges(items: list[dict], item_type: str) -> list[dict]:
    if not items:
        return items
    for it in items:
        it["ranking_badge"] = None

    if item_type == "job":
        for idx, it in enumerate(items):
            it["ranking_badge"] = get_ranking_badge(item_type, idx)
        return items

    # Base primary badge = highest score item.
    items[0]["ranking_badge"] = "rank_top"
    if len(items) == 1:
        return items

    remaining = list(range(1, len(items)))

    if item_type == "course":
        duration_pairs = []
        for idx in remaining:
            hrs = parse_duration_hours(items[idx].get("row", {}).get("duration"))
            if hrs is not None:
                duration_pairs.append((idx, hrs))
        if duration_pairs:
            fastest_idx = min(duration_pairs, key=lambda x: x[1])[0]
            items[fastest_idx]["ranking_badge"] = "rank_fast"
            remaining = [idx for idx in remaining if idx != fastest_idx]

    # Balanced badge to next best unassigned.
    if remaining:
        best_remaining = max(remaining, key=lambda i: float(items[i].get("meta", {}).get("score_pct", 0)))
        items[best_remaining]["ranking_badge"] = "rank_balanced"
        remaining = [idx for idx in remaining if idx != best_remaining]

    # Master: one additional depth-oriented badge if space exists.
    if item_type == "master" and remaining:
        deep_idx = max(
            remaining,
            key=lambda i: (
                float(items[i].get("meta", {}).get("coverage_pct", 0)),
                float(items[i].get("meta", {}).get("score_pct", 0)),
            ),
        )
        items[deep_idx]["ranking_badge"] = "rank_complete"
    return items


def normalize_job_key_part(value: str) -> str:
    txt = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return txt


def dedupe_top_jobs(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        row = item.get("row", {})
        key = (
            normalize_job_key_part(row.get("title", "")),
            normalize_job_key_part(row.get("company", "")),
            normalize_job_key_part(row.get("location", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def canonical_job_title(title: str) -> str:
    txt = normalize_job_key_part(title)
    txt = re.sub(r"\b(senior|sr|junior|jr|lead|principal|staff)\b", "", txt)
    txt = re.sub(r"\b(ai/ml|ml/ai)\b", "ml", txt)
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def diversify_top_jobs(items: list[dict], target_n: int = 3) -> list[dict]:
    if not items:
        return items
    chosen = []
    used_titles = []
    for item in items:
        if len(chosen) >= target_n:
            break
        row = item.get("row", {})
        score = float(item.get("meta", {}).get("score_pct", 0))
        canon = canonical_job_title(str(row.get("title", "")))
        is_similar = any((canon == t or canon in t or t in canon) for t in used_titles)
        if not is_similar:
            chosen.append(item)
            used_titles.append(canon)
            continue
        best_score = max(float(c.get("meta", {}).get("score_pct", 0)) for c in chosen) if chosen else score
        # If quality delta is large, keep the stronger result even if title is similar.
        if best_score - score >= 8:
            continue
        # If score is close, prefer variety and skip similar title in first pass.
        continue
    if len(chosen) < target_n:
        # Second pass: fill with unused titles first.
        for item in items:
            if len(chosen) >= target_n:
                break
            if item in chosen:
                continue
            canon = canonical_job_title(str(item.get("row", {}).get("title", "")))
            if any((canon == t or canon in t or t in canon) for t in used_titles):
                continue
            chosen.append(item)
            used_titles.append(canon)
    if len(chosen) < target_n:
        # Final pass: allow similar titles only if needed.
        for item in items:
            if len(chosen) >= target_n:
                break
            if item not in chosen:
                chosen.append(item)
    return chosen


def diversify_job_meta(items: list[dict]) -> list[dict]:
    if not items:
        return items
    raw_vals = [float(it.get("meta", {}).get("score_raw_pct", it.get("meta", {}).get("score_pct", 0))) for it in items]
    overlaps = [float(pd.to_numeric(it.get("row", {}).get("skill_overlap"), errors="coerce") or 0.0) for it in items]
    max_ov = max(overlaps) if overlaps else 1.0
    if max_ov <= 0:
        max_ov = 1.0

    composite = []
    for i, item in enumerate(items):
        raw = raw_vals[i]
        ov_sig = overlaps[i] / max_ov
        comp = 0.88 * raw + 12.0 * ov_sig
        composite.append(comp)

    cmin, cmax = min(composite), max(composite)
    for i, item in enumerate(items):
        meta = item.get("meta", {})
        if cmax > cmin:
            norm = (composite[i] - cmin) / (cmax - cmin)
            disp = 62 + norm * 34  # 62..96
        else:
            disp = raw_vals[i]
        meta["score_display"] = int(round(disp))
        item["meta"] = meta

    # Tie-break for top 3 when still identical.
    top = items[:3]
    if len(top) >= 2:
        vals = [int(it.get("meta", {}).get("score_display", 0)) for it in top]
        if len(set(vals)) == 1:
            base = vals[0]
            for i, it in enumerate(top):
                it["meta"]["score_display"] = max(0, base - i)

    # Avoid repeated interpretation label in top 3 when ties are close.
    top = items[:3]
    used = {}
    for idx, item in enumerate(top):
        label = str(item.get("meta", {}).get("strategy_label", ""))
        used[label] = used.get(label, 0) + 1
        if used[label] <= 1:
            continue
        score = float(item.get("meta", {}).get("score_display", item.get("meta", {}).get("score_pct", 0)))
        alt = None
        if score >= 84:
            alt = {"label": tr("job_label_good_fit"), "text": tr("job_insight_good_fit"), "css": "strategy-comp"}
        elif score >= 70:
            alt = {"label": tr("job_label_partial_fit"), "text": tr("job_insight_partial_fit"), "css": "strategy-gap"}
        if alt:
            item["meta"]["strategy_label"] = alt["label"]
            item["meta"]["strategy_base_text"] = alt["text"]
            item["meta"]["strategy_css"] = alt["css"]
            used[label] -= 1
            used[alt["label"]] = used.get(alt["label"], 0) + 1
    return items


def compute_recommendation_meta(
    row: pd.Series,
    reco_type: str,
    target_role: str = "",
    price_txt: str | None = None,
) -> dict:
    coverage = clamp01(row.get("coverage_score", 0.0))
    base_alignment = clamp01(row.get("semantic_score", row.get("match_score", 0.0)))
    if reco_type in {"course", "master"}:
        title_field = "title" if reco_type == "course" else "program_name"
        title_align = text_role_overlap_score(str(row.get(title_field, "")), target_role)
        alignment = adaptive_weighted_score(
            {"semantic": base_alignment, "title_role": title_align},
            {"semantic": 0.75, "title_role": 0.25},
        )
    else:
        alignment = base_alignment
    quality = quality_signal(row)
    efficiency = efficiency_signal(row, reco_type=reco_type, price_txt=price_txt)

    if reco_type in {"course", "master"}:
        weights = {"coverage": 0.50, "alignment": 0.30, "quality": 0.10, "efficiency": 0.10}
        score = adaptive_weighted_score(
            {
                "coverage": coverage,
                "alignment": alignment,
                "quality": quality,
                "efficiency": efficiency,
            },
            weights,
        )
    else:
        skill_align = clamp01(row.get("match_score", row.get("coverage_score", 0.0)))
        role_family_txt = str(row.get("role_family", "")).strip().lower()
        role_family_align = None
        if role_family_txt:
            role_family_align = 1.0 if (target_role and role_family_txt == target_role.lower()) else 0.45
        title_align = text_role_overlap_score(str(row.get("title", "")), target_role)
        semantic_align = adaptive_weighted_score(
            {"role_family": role_family_align, "title_role": title_align},
            {"role_family": 0.40, "title_role": 0.60},
        )
        if semantic_align <= 0:
            semantic_align = clamp01(row.get("match_score", 0.0) * 0.75)
        context_parts = []
        if str(row.get("seniority", "")).strip():
            context_parts.append(0.65)
        if str(row.get("location", "")).strip():
            context_parts.append(0.60)
        if str(row.get("sector", "")).strip():
            context_parts.append(0.60)
        mode_txt = str(row.get("work_mode", row.get("work_type", ""))).lower()
        if mode_txt:
            context_parts.append(0.75 if "remote" in mode_txt else 0.60)
        context_signal = (sum(context_parts) / len(context_parts)) if context_parts else None
        score = adaptive_weighted_score(
            {
                "skill_align": skill_align,
                "semantic_align": semantic_align,
                "context": context_signal,
            },
            {"skill_align": 0.60, "semantic_align": 0.25, "context": 0.15},
        )
        coverage = skill_align
        alignment = semantic_align if semantic_align is not None else skill_align

    cov_pct = int(round(coverage * 100))
    align_pct = int(round(alignment * 100))
    score_pct = int(round(clamp01(score) * 100))
    quality_pct = None if quality is None else int(round(clamp01(quality) * 100))
    eff_pct = None if efficiency is None else int(round(clamp01(efficiency) * 100))

    if reco_type in {"course", "master"}:
        if cov_pct >= 75 and align_pct >= 70:
            reason = tr("why_high_both")
        elif cov_pct >= 75:
            reason = tr("why_high_cov_mid_align")
        elif align_pct >= 75:
            reason = tr("why_mid_cov_high_align")
        else:
            reason = tr("why_general")
    else:
        reason = ""

    strategy = get_interpretation_badge(
        item_type=reco_type,
        coverage_pct=cov_pct,
        closeness_pct=align_pct,
        score_pct=score_pct,
    )

    return {
        "score_pct": score_pct,
        "score_raw_pct": round(clamp01(score) * 100.0, 2),
        "coverage_pct": cov_pct,
        "alignment_pct": align_pct,
        "alignment_score": clamp01(alignment),
        "quality_pct": quality_pct,
        "efficiency_pct": eff_pct,
        "why_text": tr("reco_why_template", reason=reason) if reason else "",
        "strategy_label": strategy.get("label", ""),
        "strategy_base_text": strategy.get("text", ""),
        "strategy_text": strategy.get("text", ""),
        "strategy_css": strategy.get("css", "strategy-low"),
        "orientation_level": "",
        "orientation_label": "",
    }


def render_skill_tag(label: str, variant: str = "neutral") -> str:
    cls = f"skill-chip {variant}".strip()
    return f"<span class='{cls}'>{escape(label)}</span>"


TRAINING_DISPLAY_LIMITS = {
    "course": 3,
    "master": 2,
}


def get_training_display_policy(score_pct: int) -> dict:
    score = int(score_pct)
    if score >= 70:
        return {
            "label": tr("training_label_high_alignment"),
            "text": tr("training_insight_high_alignment"),
            "css": "strategy-direct",
            "bucket": "high",
        }
    if score >= 60:
        return {
            "label": tr("training_label_good_goal"),
            "text": tr("training_insight_good_goal"),
            "css": "strategy-comp",
            "bucket": "good",
        }
    if score >= 50:
        return {
            "label": tr("training_label_complementary_option"),
            "text": tr("training_insight_complementary_option"),
            "css": "strategy-gap",
            "bucket": "complementary",
        }
    return {
        "label": tr("label_low_priority"),
        "text": tr("insight_low_priority"),
        "css": "strategy-low",
        "bucket": "weak",
    }


def apply_training_display_policy(items: list[dict], reco_type: str) -> tuple[list[dict], dict]:
    if reco_type not in TRAINING_DISPLAY_LIMITS:
        return items, {"has_strong_training": True}
    if not items:
        return [], {"has_strong_training": False}

    has_strong_training = any(int(it.get("meta", {}).get("score_pct", 0)) >= 50 for it in items)
    if not has_strong_training:
        return [], {"has_strong_training": False}

    filtered: list[dict] = []
    for idx, item in enumerate(items):
        score = int(item.get("meta", {}).get("score_pct", 0))
        if score < 40:
            continue
        if score < 50:
            stronger_alternatives = sum(
                1 for prev in items[:idx] if int(prev.get("meta", {}).get("score_pct", 0)) > score
            )
            if stronger_alternatives >= 3:
                continue
        filtered.append(item)

    filtered = filtered[: TRAINING_DISPLAY_LIMITS[reco_type]]
    for item in filtered:
        policy = get_training_display_policy(int(item.get("meta", {}).get("score_pct", 0)))
        item["meta"]["strategy_label"] = policy["label"]
        item["meta"]["strategy_base_text"] = policy["text"]
        item["meta"]["strategy_css"] = policy["css"]
        item["meta"]["training_bucket"] = policy["bucket"]
        item["meta"]["strategy_text"] = get_explanation_text(
            reco_type,
            {"text": policy["text"]},
            item["meta"],
            item["row"],
        )

    filtered = assign_ranking_badges(filtered, reco_type)
    for idx, item in enumerate(filtered):
        item["is_top_option"] = idx == 0
    return filtered, {"has_strong_training": True}


def render_score_badge(score_pct: int, reco_type: str = "job") -> str:
    key = "goal_alignment_percent" if reco_type in {"course", "master"} else "match_percent"
    return f"<span class='score-pill'>{escape(tr(key, value=score_pct))}</span>"


def render_recommendation_badge(badge_key: str | None) -> str:
    if not badge_key or badge_key not in RANKING_BADGE_CONFIG:
        return ""
    conf = RANKING_BADGE_CONFIG[badge_key]
    label = tr(conf["label_key"])
    tip = tr(conf["tip_key"])
    return f"<span class='top-badge {conf['css']}' title='{escape(tip)}'>{escape(label)}</span>"


def get_visible_badge_html(meta: dict, ranking_badge_key: str | None = None) -> str:
    strategy_label = escape(str(meta.get("strategy_label", "")))
    strategy_css = escape(str(meta.get("strategy_css", "strategy-gap")))
    if strategy_label:
        return f"<span class='strategy-badge {strategy_css}'>{strategy_label}</span>"
    return render_recommendation_badge(ranking_badge_key)


def get_master_gap_skills(
    master_id,
    gap_skills: list,
    master_skills_df: pd.DataFrame,
    missing_core: list = None,
    missing_important: list = None,
) -> tuple[str, list]:
    """Devuelve (skill_principal, [skills_secundarias]) del gap que cubre el máster."""
    if master_skills_df is None or master_skills_df.empty or not gap_skills:
        return "", []
    try:
        mid = str(master_id)
        master_skill_set = set(
            master_skills_df[master_skills_df["master_id"].astype(str) == mid]["skill"].str.lower().tolist()
        )
    except Exception:
        return "", []

    gap_set = set(gap_skills)
    overlap = master_skill_set & gap_set
    if not overlap:
        return "", []

    core = list(missing_core or [])
    important = list(missing_important or [])
    ordered = []
    for s in core:
        if s in overlap:
            ordered.append(s)
    for s in important:
        if s in overlap and s not in ordered:
            ordered.append(s)
    for s in sorted(overlap):
        if s not in ordered:
            ordered.append(s)

    if not ordered:
        return "", []
    return ordered[0], ordered[1:4]


def get_course_gap_skills(
    course_id,
    gap_skills: list,
    course_skills_df: pd.DataFrame,
    missing_core: list = None,
    missing_important: list = None,
) -> tuple[str, list]:
    """
    Devuelve (skill_principal, [skills_secundarias]) del gap que cubre el curso.
    Prioriza missing_core > missing_important > resto del gap.
    """
    if course_skills_df is None or course_skills_df.empty or not gap_skills:
        return "", []

    try:
        cid = str(course_id)
        course_skill_set = set(
            course_skills_df[course_skills_df["course_id"].astype(str) == cid]["skill_norm"].tolist()
        )
    except Exception:
        return "", []

    gap_set = set(gap_skills)
    overlap = course_skill_set & gap_set
    if not overlap:
        return "", []

    # Ordena por prioridad: core > important > resto
    core = list(missing_core or [])
    important = list(missing_important or [])
    ordered = []
    for s in core:
        if s in overlap:
            ordered.append(s)
    for s in important:
        if s in overlap and s not in ordered:
            ordered.append(s)
    for s in sorted(overlap):
        if s not in ordered:
            ordered.append(s)

    if not ordered:
        return "", []

    primary = ordered[0]
    secondary = ordered[1:4]  # máximo 3 secundarias
    return primary, secondary


def render_recommendation_card(
    row: pd.Series,
    reco_type: str,
    meta: dict,
    ranking_badge_key: str | None = None,
    price_txt: str | None = None,
    show_primary_metrics: bool = True,
    is_top_option: bool = False,
    gap_skills: list | None = None,
    missing_core: list | None = None,
    missing_important: list | None = None,
    course_skills_df: pd.DataFrame | None = None,
    master_skills_df: pd.DataFrame | None = None,
):
    if reco_type == "master":
        title = compact_text(clean_ui_text(row.get("program_name", tr("master_no_title"))), 72)
        provider = compact_text(clean_ui_text(row.get("university", tr("uni_missing"))), 56)
        location = compact_text(clean_ui_text(row.get("location", tr("location_missing"))), 52)
        link = str(row.get("url", "")).strip()
        cta = tr("view_program")
        show_price = True
        final_price = price_txt or master_price_label(row)
    elif reco_type == "course":
        title = compact_text(clean_ui_text(row.get("title", tr("course_no_title"))), 72)
        provider = compact_text(clean_ui_text(row.get("provider", row.get("platform", "Udemy"))), 48)
        location = ""
        link = normalize_course_url(row.get("url", ""))
        cta = tr("view_course") if link else tr("link_unavailable")
        duration_val = clean_ui_text(row.get("duration", "")).strip()
        rating = row.get("rating")
        reviews = row.get("num_reviews")
        rating_txt = f"{float(rating):.1f}/5" if pd.notna(rating) else "N/D"
        reviews_txt = f"{int(reviews):,}".replace(",", ".") if pd.notna(reviews) else "N/D"
        final_price = price_txt or format_course_price(row)
        show_price = str(final_price).strip().upper() != "N/D"
    else:
        title = compact_text(clean_ui_text(row.get("title", tr("job_no_title"))), 72)
        provider = compact_text(clean_ui_text(row.get("company", tr("company_missing"))), 48)
        location = compact_text(clean_ui_text(row.get("location", tr("location_missing"))), 52)
        link = build_job_search_link(row)
        cta = tr("go_offer")
        show_price = False
        final_price = ""
        published_txt = format_job_posted_date(row.get("date_posted", ""))
        is_recent = is_recent_job(row.get("date_posted", ""))

    badge_html = get_visible_badge_html(meta, ranking_badge_key=ranking_badge_key)
    if reco_type == "job" and is_recent:
        recent_badge = f"<span class='top-badge badge-fast'>{escape(tr('badge_recent'))}</span>"
        badge_html = f"{badge_html}{recent_badge}" if badge_html else recent_badge
    strategy_text = escape(clean_ui_text(meta.get("strategy_text", "")))

    # Para cursos: muestra skills del gap que cubre en vez del texto genérico
    course_gap_html = ""
    if reco_type == "course" and gap_skills and course_skills_df is not None:
        primary, secondary = get_course_gap_skills(
            row.get("course_id", ""),
            gap_skills,
            course_skills_df,
            missing_core=missing_core,
            missing_important=missing_important,
        )
        if primary:
            lang = st.session_state.get("lang", "es")
            primary_label = "Skill principal que refuerza" if lang == "es" else "Main skill it reinforces"
            secondary_label = "También puede ayudarte con" if lang == "es" else "Also helps with"
            primary_chip = f"<span style='background:rgba(37,99,235,0.16);border:1px solid rgba(96,165,250,0.45);color:#93C5FD;padding:2px 10px;border-radius:100px;font-size:11px;font-weight:600;'>{escape(humanize_label(primary))}</span>"
            # Barra de cobertura de skills
            covered_n = 1 + len(secondary)
            total_gap = max(len(gap_skills), 1)
            cov_pct = min(100, round(covered_n / total_gap * 100))
            cov_label = f"Cubre {covered_n} de {total_gap} skills en falta ({cov_pct}%)" if lang == "es" else f"Covers {covered_n} of {total_gap} gap skills ({cov_pct}%)"
            coverage_bar = (
                f"<div style='margin:8px 0 6px;'>"
                f"<div style='display:flex;justify-content:space-between;font-size:10px;"
                f"color:rgba(147,197,253,0.86);margin-bottom:3px;'>"
                f"<span>{'Cobertura de tu gap' if lang=='es' else 'Gap coverage'}</span>"
                f"<span style='font-weight:600;'>{cov_pct}%</span></div>"
                f"<div style='background:rgba(255,255,255,0.06);border-radius:3px;height:4px;overflow:hidden;'>"
                f"<div style='width:{cov_pct}%;height:100%;background:#60A5FA;border-radius:3px;'></div>"
                f"</div></div>"
            )
            course_gap_html = f"{coverage_bar}<div style='margin:6px 0 4px;font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:0.05em;'>{escape(primary_label)}</div><div>{primary_chip}</div>"
            if secondary:
                sec_chips = " ".join(
                    f"<span style='background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:rgba(255,255,255,0.5);padding:2px 9px;border-radius:100px;font-size:10px;'>{escape(humanize_label(s))}</span>"
                    for s in secondary
                )
                course_gap_html += f"<div style='margin-top:6px;font-size:11px;color:rgba(255,255,255,0.3);margin-bottom:3px;'>{escape(secondary_label)}</div><div>{sec_chips}</div>"
            strategy_text = ""  # oculta el texto genérico cuando hay info específica

    # Para másteres: muestra skills del gap que cubre
    master_gap_html = ""
    if reco_type == "master" and gap_skills and master_skills_df is not None:
        primary, secondary = get_master_gap_skills(
            row.get("master_id", ""),
            gap_skills,
            master_skills_df,
            missing_core=missing_core,
            missing_important=missing_important,
        )
        if primary:
            lang = st.session_state.get("lang", "es")
            primary_label = "Skill principal que refuerza" if lang == "es" else "Main skill it reinforces"
            secondary_label = "También cubre" if lang == "es" else "Also covers"
            # Barra de cobertura de skills
            covered_n = 1 + len(secondary)
            total_gap = max(len(gap_skills), 1)
            cov_pct = min(100, round(covered_n / total_gap * 100))
            coverage_bar = (
                f"<div style='margin:8px 0 6px;'>"
                f"<div style='display:flex;justify-content:space-between;font-size:10px;"
                f"color:rgba(147,197,253,0.86);margin-bottom:3px;'>"
                f"<span>{'Cobertura de tu gap' if lang=='es' else 'Gap coverage'}</span>"
                f"<span style='font-weight:600;'>{covered_n} skill{'s' if covered_n!=1 else ''} · {cov_pct}%</span></div>"
                f"<div style='background:rgba(255,255,255,0.06);border-radius:3px;height:4px;overflow:hidden;'>"
                f"<div style='width:{cov_pct}%;height:100%;background:#60A5FA;border-radius:3px;'></div>"
                f"</div></div>"
            )
            primary_chip = (
                f"<span style='background:rgba(37,99,235,0.16);border:1px solid rgba(96,165,250,0.45);"
                f"color:#93C5FD;padding:2px 10px;border-radius:100px;font-size:11px;font-weight:600;'>"
                f"{escape(humanize_label(primary))}</span>"
            )
            master_gap_html = (
                f"{coverage_bar}"
                f"<div style='margin:6px 0 4px;font-size:11px;color:rgba(255,255,255,0.4);"
                f"letter-spacing:0.05em;'>{escape(primary_label)}</div><div>{primary_chip}</div>"
            )
            if secondary:
                sec_chips = " ".join(
                    f"<span style='background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);"
                    f"color:rgba(255,255,255,0.5);padding:2px 9px;border-radius:100px;font-size:10px;'>"
                    f"{escape(humanize_label(s))}</span>"
                    for s in secondary
                )
                master_gap_html += (
                    f"<div style='margin-top:6px;font-size:11px;color:rgba(255,255,255,0.3);"
                    f"margin-bottom:3px;'>{escape(secondary_label)}</div><div>{sec_chips}</div>"
                )
            strategy_text = ""

    meta_rows: list[str] = []
    if show_primary_metrics:
        meta_rows.extend(clean_ui_text(x) for x in get_display_metrics(reco_type, meta))
    if reco_type in {"master", "course"}:
        content_brief = build_learning_content_snippet(row, reco_type, title, max_len=112)
        if content_brief:
            meta_rows.append(clean_ui_text(f"{tr('content_brief')}: {content_brief}"))
    elif reco_type == "job":
        content_brief = build_job_content_snippet(row, max_len=112)
        if content_brief:
            meta_rows.append(clean_ui_text(f"{tr('content_brief')}: {content_brief}"))
    if reco_type == "course":
        if duration_val:
            meta_rows.append(f"{tr('duration')}: {duration_val}")
        meta_rows.append(tr("course_rating", rating=rating_txt, reviews=reviews_txt))
    if reco_type == "job" and published_txt:
        meta_rows.append(tr("published_on", value=published_txt))
    if show_price:
        meta_rows.append(clean_ui_text(f"{tr('price')}: {str(final_price)}"))
    meta_rows.append(clean_ui_text(f"{tr('provider')}: {provider or tr('unknown_provider')}"))
    if location:
        meta_rows.append(clean_ui_text(location))
    meta_text = "\n".join(clean_ui_text(x) for x in meta_rows if clean_ui_text(x))
    top_choice_html = f"<span class='card-top-choice'>{escape(tr('top_choice'))}</span>" if is_top_option else ""
    card_cls = "result-card compact top-option" if is_top_option else "result-card compact"

    card_html = (
        f'<div class="{card_cls}">'
        f'{top_choice_html}'
        f'<div class="card-head"><div class="clamped-title">{escape(title)}</div></div>'
        f'<div class="card-badge-row">{badge_html}</div>'
        f'<div class="card-metrics"><div class="meta meta-block">{escape(meta_text)}</div></div>'
        f'{master_gap_html}{course_gap_html}'
        f'<p class="insight-line">{strategy_text}</p>'
        f'<div class="card-footer"><a class="card-link" href="{escape(link if link else "#")}" target="_blank">{escape(cta)}</a></div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def prepare_ranked_recommendations(
    df: pd.DataFrame,
    reco_type: str,
    limit: int | None = None,
    target_role: str = "",
    live_price_map: dict | None = None,
) -> list[dict]:
    view = df.head(limit).copy() if limit else df.copy()
    if view.empty:
        return []
    rows = []
    for _, row in view.iterrows():
        item = row.copy()
        price_txt = None
        if reco_type == "course":
            price_txt = format_course_price(item)
            if str(price_txt).strip().upper() == "N/D" and live_price_map is not None:
                live_val = live_price_map.get(item.get("course_id"))
                if live_val and live_val != "N/D":
                    price_txt = _clean_price_string(live_val)
        meta = compute_recommendation_meta(item, reco_type=reco_type, target_role=target_role, price_txt=price_txt)
        rows.append({"row": item, "meta": meta, "price_txt": price_txt})
    rows = sorted(rows, key=lambda x: x["meta"]["score_pct"], reverse=True)
    if reco_type in {"course", "master"} and rows:
        rows = calibrate_training_orientation_levels(rows)
        for item in rows:
            category = get_training_category(item["meta"])
            item["meta"]["strategy_label"] = category.get("label", item["meta"].get("strategy_label", ""))
            item["meta"]["strategy_css"] = category.get("css", item["meta"].get("strategy_css", "strategy-low"))
            item["meta"]["strategy_base_text"] = category.get("text", item["meta"].get("strategy_base_text", ""))

    if reco_type == "job":
        # FIX: ordenar por score ANTES de deduplicar para garantizar que se conserva
        # la oferta con mejor puntuación cuando hay duplicados (empresa+título+ubicación).
        rows = sorted(rows, key=lambda x: float(x.get("meta", {}).get("score_pct", 0.0)), reverse=True)
        rows = dedupe_top_jobs(rows)
        if limit is not None and limit <= 4:
            rows = diversify_top_jobs(rows, target_n=limit)
        rows = diversify_job_meta(rows)
        # Keep old offers visible, but prioritize the most recent valid posting first.
        def _job_order_key(item: dict) -> tuple[int, float, float]:
            dt = parse_job_posted_date(item["row"].get("date_posted", ""))
            ts = dt.timestamp() if dt is not None else -1.0
            score = float(item["meta"].get("score_pct", 0.0))
            return (1 if dt is not None else 0, ts, score)
        rows = sorted(rows, key=_job_order_key, reverse=True)

    for item in rows:
        item["meta"]["strategy_text"] = get_explanation_text(
            reco_type,
            {"text": item["meta"].get("strategy_base_text", "")},
            item["meta"],
            item["row"],
        )

    rows = assign_ranking_badges(rows, reco_type)
    for idx, item in enumerate(rows):
        item["is_top_option"] = idx == 0
    return rows


def render_recommendation_grid(
    items: list[dict],
    reco_type: str,
    columns_n: int = 3,
    show_primary_metrics: bool = True,
    gap_skills: list | None = None,
    missing_core: list | None = None,
    missing_important: list | None = None,
    course_skills_df: pd.DataFrame | None = None,
    master_skills_df: pd.DataFrame | None = None,
):
    if not items:
        return
    for i in range(0, len(items), columns_n):
        cols = st.columns(columns_n)
        row_items = items[i : i + columns_n]
        for col_idx, item in enumerate(row_items):
            with cols[col_idx]:
                render_recommendation_card(
                    row=item["row"],
                    reco_type=reco_type,
                    meta=item["meta"],
                    ranking_badge_key=item.get("ranking_badge"),
                    price_txt=item.get("price_txt"),
                    show_primary_metrics=show_primary_metrics,
                    is_top_option=bool(item.get("is_top_option", False)),
                    gap_skills=gap_skills,
                    missing_core=missing_core,
                    missing_important=missing_important,
                    course_skills_df=course_skills_df,
                    master_skills_df=master_skills_df,
                )


def render_master_cards(
    df: pd.DataFrame,
    limit: int | None = None,
    top_badges: bool = False,
    target_role: str = "",
    columns_n: int = 3,
    show_primary_metrics: bool = True,
    gap_skills: list | None = None,
    missing_core: list | None = None,
    missing_important: list | None = None,
    master_skills_df: pd.DataFrame | None = None,
):
    if df.empty:
        render_result_notice(tr("no_masters"), tone="warning")
        return
    items = prepare_ranked_recommendations(df, reco_type="master", limit=limit, target_role=target_role)
    if not items:
        render_result_notice(tr("no_masters"), tone="warning")
        return
    items = items[:3]
    if not top_badges:
        for item in items:
            item["ranking_badge"] = None
    render_recommendation_grid(
        items,
        reco_type="master",
        columns_n=columns_n,
        show_primary_metrics=show_primary_metrics,
        gap_skills=gap_skills,
        missing_core=missing_core,
        missing_important=missing_important,
        master_skills_df=master_skills_df,
    )


def render_course_cards(
    df: pd.DataFrame,
    live_price_map: dict | None = None,
    limit: int | None = None,
    top_badges: bool = False,
    target_role: str = "",
    columns_n: int = 3,
    show_primary_metrics: bool = True,
    gap_skills: list | None = None,
    missing_core: list | None = None,
    missing_important: list | None = None,
    course_skills_df: pd.DataFrame | None = None,
):
    if df.empty:
        render_result_notice(tr("no_courses"), tone="warning")
        return
    items = prepare_ranked_recommendations(
        df,
        reco_type="course",
        limit=limit,
        target_role=target_role,
        live_price_map=live_price_map,
    )
    if not items:
        render_result_notice(tr("no_courses"), tone="warning")
        return
    items = items[:3]
    if not top_badges:
        for item in items:
            item["ranking_badge"] = None
    render_recommendation_grid(
        items,
        reco_type="course",
        columns_n=columns_n,
        show_primary_metrics=show_primary_metrics,
        gap_skills=gap_skills,
        missing_core=missing_core,
        missing_important=missing_important,
        course_skills_df=course_skills_df,
    )


def sort_jobs_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    sort_cols = ["match_score", "skill_overlap"]
    sort_ascending = [False, False]
    if "job_ranking_score" in df.columns:
        sort_cols = ["job_ranking_score", "match_score", "skill_overlap"]
        sort_ascending = [False, False, False]
    return df.sort_values(sort_cols, ascending=sort_ascending)


def render_job_cards(
    df: pd.DataFrame,
    limit: int | None = None,
    top_badges: bool = False,
    target_role: str = "",
    columns_n: int = 3,
):
    if df.empty:
        render_result_notice(tr("no_jobs"), tone="warning")
        return
    max_rows = limit if limit else 3
    pool_rows = max(max_rows, 35)
    ranked = sort_jobs_for_display(df).head(pool_rows).reset_index(drop=True)
    items = prepare_ranked_recommendations(ranked, reco_type="job", target_role=target_role)
    items = items[:max_rows]
    if not top_badges:
        for item in items:
            item["ranking_badge"] = None
    render_recommendation_grid(items, reco_type="job", columns_n=columns_n)


def split_jobs_by_viability(jobs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if jobs is None or jobs.empty:
        return jobs, jobs
    df = jobs.copy()
    if "is_aspirational" in df.columns:
        mask = df["is_aspirational"].fillna(False).astype(bool)
    elif "seniority_fit" in df.columns:
        mask = df["seniority_fit"].fillna(0.0).astype(float) < 0.55
    else:
        mask = pd.Series(False, index=df.index)
    applicable = df[~mask].copy()
    aspirational = df[mask].copy()
    return applicable, aspirational


def get_primary_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    applicable_jobs, _ = split_jobs_by_viability(jobs)
    if isinstance(applicable_jobs, pd.DataFrame) and not applicable_jobs.empty:
        return applicable_jobs
    return jobs


def should_recommend_jobs(candidate_profile: dict) -> bool:
    # Kept for backward compatibility with old calls.
    assessment = assess_job_readiness(candidate_profile, target_role="other_data_role")
    return bool(assessment.get("eligible", False))


def get_jobs_blocked_reason(
    rec: dict,
    candidate_profile: dict,
    readiness: dict,
    target_role: str,
    lang: str = "es",
) -> str:
    skills = set(candidate_profile.get("skills_detected", []) or [])
    technical_verified = int(readiness.get("technical_verified", 0) or 0)
    has_data_master = bool(candidate_profile.get("has_data_related_master", False))
    has_python = "python" in skills
    has_sql = "sql" in skills
    has_bi = bool(skills & {"power_bi", "tableau", "looker", "qlik"})
    has_ml = bool(skills & {"machine_learning", "deep_learning", "scikit_learn"})
    domain_exp = float(readiness.get("domain_exp", 0) or 0)
    non_intern_exp = float(readiness.get("non_intern_exp", 0) or 0)
    readiness_score = float(
        readiness.get("readiness_score", readiness.get("score", 0)) or 0
    )

    is_strict = target_role in {"ml_engineer", "data_scientist", "data_engineer"}
    missing = []

    if is_strict:
        min_tech = 2 if has_data_master else 3
        if technical_verified < min_tech:
            n = min_tech - technical_verified
            if lang == "es":
                missing.append(
                    f"{n} skill{'s técnicas' if n > 1 else ' técnica'} "
                    f"verificada{'s' if n > 1 else ''} más"
                )
            else:
                missing.append(
                    f"{n} more verified technical skill{'s' if n > 1 else ''}"
                )
        if not has_python:
            missing.append("Python")
        if not has_sql:
            missing.append("SQL")
        if not has_ml and domain_exp < 0.7 and non_intern_exp < 1.0:
            if lang == "es":
                missing.append("Machine Learning, Deep Learning o Scikit-learn")
            else:
                missing.append("Machine Learning, Deep Learning or Scikit-learn")
    else:
        if technical_verified < 2:
            n = 2 - technical_verified
            if lang == "es":
                missing.append(
                    f"{n} skill{'s técnicas' if n > 1 else ' técnica'} "
                    f"verificada{'s' if n > 1 else ''}"
                )
            else:
                missing.append(
                    f"{n} verified technical skill{'s' if n > 1 else ''}"
                )
        if not (has_python or has_sql or has_bi):
            if lang == "es":
                missing.append("Python, SQL o una herramienta BI (Power BI, Tableau)")
            else:
                missing.append("Python, SQL or a BI tool (Power BI, Tableau)")
        if readiness_score < 0.38:
            if lang == "es":
                missing.append("mayor evidencia de experiencia práctica en datos")
            else:
                missing.append("more evidence of hands-on data experience")

    if not missing:
        return tr("jobs_blocked_non_data")

    if len(missing) == 1:
        items_str = missing[0]
    elif len(missing) == 2:
        items_str = (
            f"{missing[0]} y {missing[1]}"
            if lang == "es"
            else f"{missing[0]} and {missing[1]}"
        )
    else:
        sep = " y " if lang == "es" else " and "
        items_str = ", ".join(missing[:-1]) + sep + missing[-1]

    core_gap = list(rec.get("missing_core_skills", []) or [])
    important_gap = list(rec.get("missing_important_skills", []) or [])
    top_gap = (core_gap + [s for s in important_gap if s not in core_gap])[:3]
    if top_gap:
        gap_labels = ", ".join(humanize_label(s) for s in top_gap)
        if lang == "es":
            gap_line = f"Tus gaps más prioritarios para el rol son: {gap_labels}."
        else:
            gap_line = f"Your top priority gaps for this role are: {gap_labels}."
    else:
        gap_line = ""

    if lang == "es":
        msg = (
            f"Para ver ofertas de empleo para este rol necesitas: "
            f"{items_str}. "
            f"La ruta formativa recomendada te ayudará a conseguirlo."
        )
    else:
        msg = (
        f"To unlock job listings for this role you need: "
        f"{items_str}. "
        f"The recommended learning path will help you get there."
        )

    if gap_line:
        msg = msg + " " + gap_line

    return msg


def assess_job_readiness(candidate_profile: dict, target_role: str) -> dict:
    profile = candidate_profile or {}
    skills = {str(s).strip().lower() for s in profile.get("skills_detected", []) if str(s).strip()}
    evidence_map = {str(k).strip().lower(): str(v).strip().lower() for k, v in (profile.get("skills_evidence", {}) or {}).items()}

    # Pesos por importancia real en el mercado
    SKILL_WEIGHTS = {
        # Tier 1 – fundamentales (sin estos no hay perfil de datos)
        "python": 2.0, "sql": 2.0,
        # Tier 2 – muy valorados
        "r": 1.5, "machine_learning": 1.5, "deep_learning": 1.5,
        "scikit_learn": 1.5, "spark": 1.5, "dbt": 1.5,
        "airflow": 1.5, "databricks": 1.5,
        # Tier 3 – importantes pero más comunes
        "etl": 1.2, "data_engineering": 1.2, "statistics": 1.2,
        "aws": 1.0, "azure": 1.0, "gcp": 1.0,
        "docker": 1.0, "kubernetes": 1.0,
        "pandas": 1.0, "numpy": 1.0,
        "power_bi": 1.0, "tableau": 1.0,
        # Tier 4 – complementarios
        "data_visualization": 0.8, "forecasting": 0.8,
        "experimentation": 0.8, "api": 0.8,
        # Tier 5 – muy genéricos / baja diferenciación
        "excel": 0.5,
    }
    strong_skills = set(SKILL_WEIGHTS.keys())
    abstract_skills = {
        "data_analysis", "analytical_thinking", "reporting", "insights", "business_intelligence",
        "problem_solving", "communication", "strategy",
    }
    verified_evidence = {"professional", "project", "academic"}

    technical_detected = {s for s in skills if s in strong_skills}
    technical_verified = {s for s in technical_detected if evidence_map.get(s, "declared") in verified_evidence}
    abstract_only = {s for s in skills if s in abstract_skills}
    has_python = "python" in technical_detected
    has_sql = "sql" in technical_detected
    has_bi = bool({"power_bi", "tableau", "excel"} & technical_detected)
    has_ml = bool({"machine_learning", "deep_learning", "scikit_learn"} & technical_detected)

    domains = profile.get("experience_years_relevant_by_domain", {}) or {}
    domain_exp = float(sum(float(domains.get(k, 0.0)) for k in [
        "data_analytics", "machine_learning", "nlp", "llm_genai", "data_engineering", "bi_reporting",
    ]))
    non_intern_exp = float(profile.get("experience_years_non_intern", 0.0) or 0.0)
    edu_signal = 1.0 if profile.get("graduation_year") else 0.0
    edu_role_rel = float((profile.get("education_relevance_by_role", {}) or {}).get(target_role, profile.get("education_data_relevance", 0.0)) or 0.0)
    has_data_master = bool(profile.get("has_data_related_master", False))

    family = str(target_role or "").lower()
    strict_family = family in {"data_scientist", "ml_engineer", "data_engineer"}
    analyst_family = family in {"data_analyst", "other_data_role"}

    # Readiness score favors verified technical evidence over abstract mention.
    readiness_score = (
        0.45 * min(1.0, len(technical_verified) / 4.0)
        + 0.20 * min(1.0, len(technical_detected) / 6.0)
        + 0.20 * min(1.0, domain_exp / 1.5)
        + 0.08 * min(1.0, non_intern_exp / 2.0)
        + 0.03 * edu_signal
        + 0.04 * min(1.0, edu_role_rel)
    )
    if has_data_master:
        readiness_score = min(1.0, readiness_score + 0.05)
    if len(technical_verified) == 0 and len(abstract_only) > 0:
        readiness_score *= 0.55

    stage = "no_base"
    if readiness_score >= 0.66:
        stage = "ready"
    elif readiness_score >= 0.46:
        stage = "bridge"
    elif readiness_score >= 0.24:
        stage = "base"
    if non_intern_exp < 0.25 and len(technical_verified) < 3 and stage == "ready":
        stage = "bridge"

    eligible = False
    if strict_family:
        eligible = (
            len(technical_verified) >= (2 if has_data_master else 3)
            and has_python
            and has_sql
            and (has_ml or domain_exp >= 0.7 or non_intern_exp >= 1.0)
        )
        if non_intern_exp < 0.25 and len(technical_verified) < 4:
            eligible = False
    elif analyst_family:
        eligible = (
            len(technical_verified) >= 2
            and (has_python or has_sql or has_bi)
            and readiness_score >= 0.38
        )
    else:
        eligible = readiness_score >= 0.5 and len(technical_verified) >= 2

    # Bridge profiles can see jobs only for analyst-like families.
    if (not eligible) and stage == "bridge" and analyst_family and len(technical_verified) >= 2:
        eligible = True
    # Soft unlock ponderado: la suma de pesos de skills detectados debe alcanzar
    # un umbral mínimo (Python+SQL = 4.0, Python+pandas+SQL = 5.0, etc.)
    # Así Excel+Tableau+PowerBI (2.5) no desbloquea, pero Python+SQL (4.0) sí.
    weighted_technical = sum(SKILL_WEIGHTS.get(s, 0.8) for s in technical_detected)
    if (not eligible) and weighted_technical >= 3.5 and readiness_score >= 0.28:
        eligible = True

    return {
        "eligible": bool(eligible),
        "stage": stage,
        "score": round(float(readiness_score), 3),
        "technical_verified": len(technical_verified),
        "technical_detected": len(technical_detected),
        "has_python": bool(has_python),
        "has_sql": bool(has_sql),
        "has_ml": bool(has_ml),
        "non_intern_exp": round(non_intern_exp, 2),
        "domain_exp": round(domain_exp, 2),
        "education_role_relevance": round(edu_role_rel, 2),
        "has_data_related_master": has_data_master,
    }


def infer_profile_family(candidate_profile: dict, role_label: str) -> str:
    domains = (candidate_profile or {}).get("experience_years_relevant_by_domain", {}) or {}
    domain_map = {
        "data_analytics": "Data / Analytics",
        "bi_reporting": "BI / Reporting",
        "machine_learning": "Machine Learning",
        "data_engineering": "Data Engineering",
        "llm_genai": "GenAI / LLM",
        "nlp": "NLP",
    }
    best_key, best_val = None, 0.0
    for k, v in domains.items():
        fv = float(v or 0.0)
        if fv > best_val:
            best_key, best_val = k, fv
    if best_key and best_key in domain_map and best_val >= 0.15:
        return domain_map[best_key]
    return role_label


def get_priority_gap_skills(rec: dict, limit: int | None = None) -> list[str]:
    core_gap = list(rec.get("missing_core_skills", []) or [])
    important_gap = list(rec.get("missing_important_skills", []) or [])
    all_gap = list(rec.get("gap_skills", []) or [])
    priority_gap = (
        core_gap
        + [s for s in important_gap if s not in core_gap]
        + [s for s in all_gap if s not in core_gap and s not in important_gap]
    )
    return priority_gap[:limit] if limit is not None else priority_gap


def render_profile_summary_block(candidate_profile: dict, candidate_skills: set[str], rec: dict, role_label: str):
    strengths = [humanize_label(s) for s in sorted(candidate_skills)[:4]]
    if bool((candidate_profile or {}).get("has_data_related_master", False)):
        strengths = strengths + [tr("data_master_detected")]
    core_gap = list(rec.get("missing_core_skills", []) or [])
    important_gap = list(rec.get("missing_important_skills", []) or [])
    all_gap = list(rec.get("gap_skills", []) or [])
    priority_gap = (
        core_gap
        + [s for s in important_gap if s not in core_gap]
        + [s for s in all_gap if s not in core_gap and s not in important_gap]
    )
    gap = [humanize_label(s) for s in priority_gap[:4]]
    profile_name = infer_profile_family(candidate_profile, role_label)
    focus = tr("profile_focus_default")
    if bool((candidate_profile or {}).get("has_data_related_master", False)):
        postgrad_status = tr("postgrad_data_yes")
    elif bool((candidate_profile or {}).get("has_master_degree", False)):
        postgrad_status = tr("postgrad_master_non_data")
    else:
        postgrad_status = tr("postgrad_none")
    if len(rec.get("gap_skills", [])) <= 6:
        focus = "Aplicar a roles objetivo + reforzar experiencia real" if st.session_state.get("lang", "es") == "es" else "Apply to target roles + strengthen hands-on experience"
    st.markdown(
        f"""
        <div class="profile-summary">
          <div class="ps-title">{escape(tr("profile_detected_summary"))}</div>
          <div class="ps-grid">
            <div class="ps-item">
              <div class="ps-label">{escape(tr("profile_detected"))}</div>
              <div class="ps-value">{escape(profile_name)}</div>
            </div>
            <div class="ps-item">
              <div class="ps-label">{escape(tr("profile_strengths"))}</div>
              <div class="ps-value">{escape(", ".join(strengths) if strengths else tr("no_data"))}</div>
            </div>
            <div class="ps-item">
              <div class="ps-label">{escape(tr("profile_gap_main"))}</div>
              <div class="ps-value">{escape(", ".join(gap) if gap else tr("no_data"))}</div>
            </div>
            <div class="ps-item">
              <div class="ps-label">{escape(tr("profile_focus"))}</div>
              <div class="ps-value">{escape(focus)}</div>
            </div>
            <div class="ps-item">
              <div class="ps-label">{escape(tr("postgrad_status"))}</div>
              <div class="ps-value">{escape(postgrad_status)}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_coursera_alternatives(rec: dict, coursera_df: pd.DataFrame):
    if coursera_df is None or coursera_df.empty:
        return
    gap = [str(s or "").strip().lower() for s in rec.get("gap_skills", []) if str(s or "").strip()]
    if not gap:
        return
    tmp = coursera_df.copy()
    if "keyword" in tmp.columns:
        tmp["keyword_norm"] = tmp["keyword"].astype(str).str.lower().str.strip()
        pick = tmp[tmp["keyword_norm"].isin(gap)]
        if pick.empty:
            pick = tmp[tmp["keyword_norm"].isin(gap[:3])]
    else:
        pick = tmp
    if pick.empty:
        return
    cols = [c for c in ["title", "course_url", "price_text", "price_type", "provider", "keyword"] if c in pick.columns]
    pick = pick[cols].drop_duplicates(subset=["course_url"] if "course_url" in cols else ["title"]).head(8)
    st.markdown(f"### {tr('coursera_reco')}")
    for _, row in pick.iterrows():
        title = escape(str(row.get("title", "Coursera course")))
        url = escape(str(row.get("course_url", "#")))
        ptxt = escape(str(row.get("price_text", "N/D")))
        ptype = escape(str(row.get("price_type", "unknown")))
        kw = escape(humanize_label(str(row.get("keyword", ""))))
        st.markdown(
            f"""
            <div class="result-card">
              <div class="card-head">
                <h4>{title}</h4>
                <span class="score-pill">Coursera</span>
              </div>
              <p class="meta">Keyword: {kw}</p>
              <p class="meta">{tr("price")}: {ptxt}</p>
              <p class="meta">{tr("price_type")}: {ptype}</p>
              <a class="card-link" href="{url}" target="_blank">{tr("view_course")}</a>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_missing_skill_plan(skill_course_map: dict):
    st.markdown(f"### {tr('plan_missing')}")
    if not skill_course_map:
        render_result_notice(tr("missing_skill_none"), tone="info")
        return
    for skill, courses in skill_course_map.items():
        st.markdown(f"#### {humanize_label(skill)}")
        if not courses:
            st.markdown(f"- {tr('missing_skill_no_course')}")
            continue
        for c in courses:
            title = escape(str(c.get("title", "Curso recomendado")))
            url = normalize_course_url(c.get("url", ""))
            rating = c.get("rating")
            rating_txt = f"{float(rating):.1f}/5" if pd.notna(rating) else "N/D"
            duration = escape(str(c.get("duration", "N/D")))
            if url:
                st.markdown(f"- [{title}]({url}) | Rating: {rating_txt} | Duración: {duration}")
            else:
                st.markdown(f"- {title} | Rating: {rating_txt} | Duración: {duration}")


def render_brand_header():
    st.markdown(
        """
        <div style="padding: 80px 40px 60px; text-align:center;">

          <div style="font-size:11px; letter-spacing:0.2em; text-transform:uppercase;
                      color:rgba(10,240,200,0.6); border:1px solid rgba(10,240,200,0.2);
                      display:inline-block; padding:6px 18px; border-radius:100px;
                      margin-bottom:48px;">
            CAREER NAVIGATOR
          </div>

          <div class="hero-wordmark">
            CAI<span class="q">Q</span>
          </div>

          <div class="acronym">
            Career Alignment and Insight Qualifier
          </div>

          <div class="hero-headline">
            Define tu próximo paso en Data, IA y Analytics
          </div>

          <div class="hero-sub">
            Descubre qué rol encaja contigo y qué habilidades
            necesitas para avanzar en el mundo de los datos.
          </div>

        </div>
        """,
        unsafe_allow_html=True,
    )
    chip_cols = st.columns(5)
    chip_labels = [
        tr("hero_chip_cv"),
        tr("hero_chip_gap"),
        tr("hero_chip_roadmap"),
        tr("hero_chip_masters"),
        tr("hero_chip_jobs"),
    ]
    for i, (c, lbl) in enumerate(zip(chip_cols, chip_labels)):
        with c:
            st.button(lbl, key=f"hero_chip_btn_{i}", disabled=True, use_container_width=True)


def render_flow_strip():
    st.markdown(
        f"""
        <div class="flow-strip-wrap" id="flow-steps">
          <div class="flow-strip-title">{escape(tr("flow_title"))}</div>
          <div class="flow-strip">
          <div class="flow-step">{tr("step1")}</div>
          <div class="flow-step">{tr("step2")}</div>
          <div class="flow-step">{tr("step3")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quick_summary(jobs: pd.DataFrame, rec: dict):
    jobs_for_top = get_primary_jobs(jobs)
    top_job = tr("no_data")
    if isinstance(jobs_for_top, pd.DataFrame) and not jobs_for_top.empty and "title" in jobs_for_top.columns:
        top_job = str(sort_jobs_for_display(jobs_for_top).iloc[0].get("title", tr("no_data")))

    next_course = tr("no_data")
    top_courses = rec.get("top_courses")
    if isinstance(top_courses, pd.DataFrame) and not top_courses.empty:
        next_course = str(top_courses.iloc[0].get("title", tr("no_data")))

    gap_skills = get_priority_gap_skills(rec, limit=3)
    gap_txt = ", ".join(humanize_label(s) for s in gap_skills) if gap_skills else tr("no_data")

    st.markdown(f"### {tr('quick_summary')}")
    st.markdown(
        f"""
        <div class="quick-grid">
          <div class="quick-card">
            <div class="quick-label">{tr("best_job")}</div>
            <div class="quick-value">{escape(top_job)}</div>
          </div>
          <div class="quick-card">
            <div class="quick-label">{tr("next_course")}</div>
            <div class="quick-value">{escape(next_course)}</div>
          </div>
          <div class="quick-card">
            <div class="quick-label">{tr("top_gap_skills")}</div>
            <div class="quick-value">{escape(gap_txt)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_skill_gap_radar(
    candidate_skills_explicit: set[str],
    rec: dict,
    data: dict,
    target_role: str,
    max_skills: int = 10,
):
    """Top skills del rol como pills — reemplaza el radar chart."""
    lang = st.session_state.get("lang", "es")

    role_skill_demand = data.get("role_skill_demand", pd.DataFrame())
    if role_skill_demand is None or role_skill_demand.empty:
        return

    role_df = role_skill_demand[
        role_skill_demand["role_family"].str.lower() == str(target_role or "").lower()
    ].copy()
    if role_df.empty:
        return

    sort_col = "demand_ratio" if "demand_ratio" in role_df.columns else (
        "demand_count" if "demand_count" in role_df.columns else None
    )
    if sort_col:
        role_df = role_df.sort_values(sort_col, ascending=False)
    top_skills_raw = list(role_df["skill"].dropna().astype(str).str.lower().unique()[:max_skills])
    if not top_skills_raw:
        return

    def _canon(s: str) -> str:
        s = str(s or "").strip().lower()
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s

    candidate_norm  = {_canon(s) for s in candidate_skills_explicit}
    gap_set         = {_canon(s) for s in rec.get("gap_skills", [])}
    remaining       = {_canon(s) for s in rec.get("remaining_gap", [])}
    covered_by_path = gap_set - remaining

    pills_html = ""
    for skill_raw in top_skills_raw:
        skill_norm = _canon(skill_raw)
        label = skill_raw.replace("_", " ").title()
        has_it  = skill_norm in candidate_norm
        covered = (not has_it) and (skill_norm in covered_by_path)
        if has_it:
            style = (
                "background:rgba(139,92,246,0.15);"
                "border:1px solid rgba(139,92,246,0.45);"
                "color:#8B5CF6;"
            )
        elif covered:
            style = (
                "background:rgba(10,240,200,0.08);"
                "border:1px solid rgba(10,240,200,0.3);"
                "color:#0AF0C8;"
            )
        else:
            style = (
                "background:rgba(255,255,255,0.04);"
                "border:1px solid rgba(255,255,255,0.1);"
                "color:rgba(255,255,255,0.28);"
            )
        pills_html += (
            f'<span style="{style}padding:5px 14px;border-radius:20px;'
            f'font-size:12px;white-space:nowrap;">{label}</span>'
        )

    if lang == "es":
        legend_have    = "En tu CV"
        legend_covered = "La ruta lo trabaja"
        section_title  = f"TOP SKILLS — {target_role.replace('_', ' ').upper()}"
    else:
        legend_have    = "In your CV"
        legend_covered = "Path covers it"
        section_title  = f"TOP SKILLS — {target_role.replace('_', ' ').upper()}"

    html = (
        '<div style="margin:24px 0 8px;">'
        f'<div style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase;'
        f'color:rgba(10,240,200,0.6);margin-bottom:14px;">{section_title}</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;">{pills_html}</div>'
        '<div style="display:flex;gap:20px;font-size:11px;color:rgba(255,255,255,0.4);">'
        f'<span><span style="color:#8B5CF6;margin-right:4px;">&#9632;</span>{legend_have}</span>'
        f'<span><span style="color:#0AF0C8;margin-right:4px;">&#9632;</span>{legend_covered}</span>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
def render_skills_intelligence(candidate_skills_explicit: set[str], rec: dict):
    target_set = set(rec.get("target_skills", []))
    gap_set = set(rec.get("gap_skills", []))
    remaining = set(rec.get("remaining_gap", []))
    covered_by_path = sorted(gap_set - remaining)

    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"]:has(> div > .skills-intel-block) {
      background: #0C1628 !important;
      border: 1px solid rgba(10,240,200,0.15) !important;
      border-radius: 12px !important;
      padding: 16px 20px !important;
      margin: 8px 0 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown(f'<div class="skills-intel-block" style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:rgba(10,240,200,0.6);margin-bottom:4px;">{tr("skills_intel")}</div>', unsafe_allow_html=True)
        core_cov = float(rec.get("role_core_coverage", 0.0) or 0.0)
        missing_core_n = len(rec.get("missing_core_skills", []) or [])
        missing_important_n = len(rec.get("missing_important_skills", []) or [])
        missing_complementary_n = len(rec.get("missing_complementary_skills", []) or [])
        st.caption(tr("skills_summary_line", detected=len(candidate_skills_explicit)))
        if core_cov >= 0.65:
            st.caption(tr("skills_summary_core_good"))
        elif core_cov >= 0.35:
            st.caption(tr("skills_summary_core_mid"))
        else:
            st.caption(tr("skills_summary_core_low"))
        if missing_core_n <= 2 and (missing_complementary_n + missing_important_n) >= 4:
            st.caption(tr("skills_summary_missing_focus"))
        elif missing_core_n >= 4:
            st.caption(tr("skills_summary_missing_advanced"))
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:#ffffff;margin-bottom:8px;background:transparent;">{tr("skills_detected_short")} ({len(candidate_skills_explicit)})</div>', unsafe_allow_html=True)
            render_skill_chips(
                sorted(candidate_skills_explicit),
                variant="detected",
                max_items=10,
                state_key="skills_detected_expand",
            )
        with c2:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:#ffffff;margin-bottom:8px;background:transparent;">{tr("skills_gap_short")} ({len(gap_set)})</div>', unsafe_allow_html=True)
            render_skill_chips(
                get_priority_gap_skills(rec),
                variant="missing",
                max_items=10,
                state_key="skills_missing_expand",
            )
        with c3:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:#ffffff;margin-bottom:8px;background:transparent;">{tr("skills_covered_short")} ({len(covered_by_path)})</div>', unsafe_allow_html=True)
            render_skill_chips(
                covered_by_path,
                variant="covered",
                max_items=10,
                state_key="skills_covered_expand",
            )


def render_explainability_panel(rec: dict, jobs: pd.DataFrame):
    jobs_for_top = get_primary_jobs(jobs)
    target_n = max(len(rec.get("target_skills", [])), 1)
    gap_n = len(rec.get("gap_skills", []))
    rem_n = len(rec.get("remaining_gap", []))
    gap_reduction = max(0, gap_n - rem_n)
    reduction_pct = round((gap_reduction / target_n) * 100)

    st.markdown(f"**{tr('reco_reason')}**")
    st.caption(tr("explain_reco_intro"))
    render_result_notice(tr("explain_reco_tooltip"), tone="info")

    c1, c2 = st.columns(2)
    with c1:
        st.caption(
            f"{tr('reduces_gap')}: {gap_reduction} ({reduction_pct}%)  |  "
            f"{tr('impact_employability')}: {max(0, min(100, round((1 - rem_n / target_n) * 100)))} / 100"
        )
        covered = sorted(set(rec.get("target_skills", [])) - set(rec.get("remaining_gap", [])))
        st.markdown(f"**{tr('covers_skills')} ({len(covered)})**")
        render_skill_chips(covered[:12])

    with c2:
        st.markdown(f"**{tr('next_best_step')}**")
        top_master = tr("no_data")
        if isinstance(rec.get("top_masters"), pd.DataFrame) and not rec["top_masters"].empty:
            top_master = str(rec["top_masters"].iloc[0].get("program_name", tr("no_data")))
        top_course = tr("no_data")
        if isinstance(rec.get("top_courses"), pd.DataFrame) and not rec["top_courses"].empty:
            top_course = str(rec["top_courses"].iloc[0].get("title", tr("no_data")))
        top_job = tr("no_data")
        if isinstance(jobs_for_top, pd.DataFrame) and not jobs_for_top.empty:
            top_job = str(sort_jobs_for_display(jobs_for_top).iloc[0].get("title", tr("no_data")))
        st.markdown(f"- **{tr('top_master')}:** {top_master}")
        st.markdown(f"- **{tr('top_course')}:** {top_course}")
        st.markdown(f"- **{tr('top_job')}:** {top_job}")


def render_recommendation_section_tabs(
    rec: dict,
    jobs: pd.DataFrame,
    data: dict,
    live_price_map: dict | None,
    target_role: str,
):
    applicable_jobs, aspirational_jobs = split_jobs_by_viability(jobs)
    jobs_for_top = get_primary_jobs(jobs)
    candidate_profile = rec.get("candidate_profile", {}) or {}
    has_data_master = bool(candidate_profile.get("has_data_related_master", False))
    has_master = bool(candidate_profile.get("has_master_degree", False))

    def _get_master_recommendation_context(profile: dict) -> dict:
        # Prepared for future toggle:
        # route_mode can evolve into {"with_master", "without_master", "auto"}.
        if bool(profile.get("has_data_related_master", False)):
            return {
                "state": "has_data_master",
                "note_key": "masters_context_has_data_master",
                "top_title_key": "top_master_optional",
                "all_title_key": "masters_recommended_optional",
                "route_mode": "auto",
            }
        if bool(profile.get("has_master_degree", False)):
            return {
                "state": "has_master_non_data",
                "note_key": "masters_context_has_master_non_data",
                "top_title_key": "top_master_bridge",
                "all_title_key": "masters_recommended_bridge",
                "route_mode": "auto",
            }
        return {
            "state": "no_master",
            "note_key": "masters_context_no_master",
            "top_title_key": "top_master",
            "all_title_key": "masters_recommended",
            "route_mode": "auto",
        }

    master_ctx = _get_master_recommendation_context(candidate_profile)

    def _render_master_context_note():
        note_key = str(master_ctx.get("note_key", "") or "")
        if note_key:
            render_result_notice(tr(note_key), tone="info")

    priority_gap_skills = prioritize_gap_skills(
        rec.get("gap_skills", []),
        data.get("role_skill_demand", pd.DataFrame()),
        target_role=target_role,
        max_skills=3,
    )
    top_courses_goal = build_goal_top_courses(
        rec.get("top_courses", pd.DataFrame()),
        priority_gap_skills=priority_gap_skills,
        courses_feat=data.get("courses_feat", pd.DataFrame()),
        course_skills=data.get("course_skills", pd.DataFrame()),
        max_courses=3,
    )

    tabs = st.tabs(
        [
            tr("top_picks"),
            tr("all_masters"),
            tr("all_courses"),
            tr("all_jobs"),
            tr("explain_ai"),
        ]
    )

    with tabs[0]:
        t1, t2, t3 = st.columns(3)
        with t1:
            render_result_h3(tr(str(master_ctx.get("top_title_key", "top_master"))))
            _render_master_context_note()
            render_master_cards(
                rec["top_masters"],
                limit=3,
                top_badges=True,
                target_role=target_role,
                columns_n=1,
                show_primary_metrics=False,
                gap_skills=rec.get("gap_skills", []),
                missing_core=rec.get("missing_core_skills", []),
                missing_important=rec.get("missing_important_skills", []),
                master_skills_df=data.get("master_skills"),
            )
        with t2:
            render_result_h3(tr("top_course"))
            render_course_cards(
                top_courses_goal,
                live_price_map=live_price_map,
                limit=3,
                top_badges=True,
                target_role=target_role,
                columns_n=1,
                show_primary_metrics=False,
                gap_skills=rec.get("gap_skills", []),
                missing_core=rec.get("missing_core_skills", []),
                missing_important=rec.get("missing_important_skills", []),
                course_skills_df=data.get("course_skills"),
            )
        with t3:
            render_result_h3(tr("top_job"))
            render_job_cards(jobs_for_top, limit=3, top_badges=True, target_role=target_role, columns_n=1)

    with tabs[1]:
        render_result_h3(tr(str(master_ctx.get("all_title_key", "masters_recommended"))))
        _render_master_context_note()
        render_master_cards(
            rec["top_masters"],
            target_role=target_role,
            gap_skills=rec.get("gap_skills", []),
            missing_core=rec.get("missing_core_skills", []),
            missing_important=rec.get("missing_important_skills", []),
            master_skills_df=data.get("master_skills"),
        )

    with tabs[2]:
        render_result_h3(tr("courses_recommended"))
        render_course_cards(
            rec["top_courses"],
            live_price_map=live_price_map,
            target_role=target_role,
            gap_skills=rec.get("gap_skills", []),
            missing_core=rec.get("missing_core_skills", []),
            missing_important=rec.get("missing_important_skills", []),
            course_skills_df=data.get("course_skills"),
        )

    with tabs[3]:
        render_result_h3(tr("jobs_applicable"))
        if applicable_jobs.empty:
            render_result_notice(tr("no_jobs_applicable"), tone="info")
        else:
            render_job_cards(applicable_jobs, target_role=target_role)
        if not aspirational_jobs.empty:
            render_result_h3(tr("jobs_aspirational"))
            render_job_cards(aspirational_jobs, target_role=target_role)

    with tabs[4]:
        render_explainability_panel(rec, jobs)
        skill_course_map = build_skill_course_map(rec["gap_skills"], data["courses_feat"], data["course_skills"], max_courses=3)
        render_missing_skill_plan(skill_course_map)
        render_coursera_alternatives(rec, data.get("coursera_prices", pd.DataFrame()))


def render_results_panel(
    rec: dict,
    jobs: pd.DataFrame,
    role_label: str,
    candidate_skills_explicit: set[str],
    candidate_profile: dict,
    candidate_skills: set[str],
    data: dict,
    live_price_map: dict,
    target_role: str,
    run_btn: bool,
    stage_label: str,
):
    st.markdown("""
<style>

/* METRICS */
[data-testid="stMetricValue"] {
  color: #0AF0C8 !important;
  font-size: 52px !important;
  font-weight: 800 !important;
}
[data-testid="stMetricLabel"] {
  color: rgba(255,255,255,0.4) !important;
  font-size: 10px !important;
  letter-spacing: 0.18em !important;
  text-transform: uppercase !important;
}

/* CAPTION */
[data-testid="stCaptionContainer"] p {
  color: rgba(255,255,255,0.35) !important;
  font-size: 11px !important;
}

/* TABS */
[data-testid="stTabs"] [role="tablist"] {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 10px !important;
  padding: 4px !important;
  gap: 2px !important;
}
[data-testid="stTabs"] [role="tab"] {
  background: transparent !important;
  color: rgba(255,255,255,0.4) !important;
  border: none !important;
  border-radius: 7px !important;
  font-size: 13px !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: rgba(10,240,200,0.1) !important;
  color: #0AF0C8 !important;
  border-bottom: 2px solid #0AF0C8 !important;
}

/* EXPANDER */
[data-testid="stExpander"] {
  background: #0C1628 !important;
  border: 1px solid rgba(10,240,200,0.15) !important;
  border-radius: 12px !important;
}
[data-testid="stExpander"] > div,
[data-testid="stExpander"] > div > div,
[data-testid="stExpander"] details,
[data-testid="stExpander"] details > div {
  background: #0C1628 !important;
}
[data-testid="stExpander"] summary p {
  color: #ffffff !important;
  font-weight: 600 !important;
}

/* BUTTONS */
.stButton > button {
  background: rgba(255,255,255,0.04) !important;
  color: rgba(255,255,255,0.6) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
}
/* Botones habilitados (Ver más / Ver menos): contraste real */
.stButton > button:not([disabled]) {
  background: #ffffff !important;
  color: #0B1F3A !important;
  border: 1px solid #bfdbfe !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(15,23,42,0.18) !important;
}
/* Garantizar que el texto dentro del botón sea teal */
.stButton > button:not([disabled]) p,
.stButton > button:not([disabled]) span {
  color: #0B1F3A !important;
  -webkit-text-fill-color: #0B1F3A !important;
}
.stButton > button:not([disabled]):hover {
  border-color: #60a5fa !important;
  color: #0B1F3A !important;
  background: #eff6ff !important;
}
/* Botón de descarga PDF */
[data-testid="stDownloadButton"] > button {
  background: #ffffff !important;
  color: #0B1F3A !important;
  border: 1px solid #bfdbfe !important;
  font-weight: 700 !important;
  width: 100% !important;
  box-shadow: 0 4px 14px rgba(15,23,42,0.18) !important;
}
[data-testid="stDownloadButton"] > button p,
[data-testid="stDownloadButton"] > button span {
  color: #0B1F3A !important;
  -webkit-text-fill-color: #0B1F3A !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: #eff6ff !important;
  border-color: #60a5fa !important;
}

/* TABS — brighter inactive text */
[data-testid="stTabs"] [role="tab"] {
  background: transparent !important;
  color: rgba(255,255,255,0.65) !important;
  border: none !important;
  border-radius: 7px !important;
  font-size: 13px !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: rgba(10,240,200,0.1) !important;
  color: #0AF0C8 !important;
  border-bottom: 2px solid #0AF0C8 !important;
}

/* EXPANDER header brighter */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {
  color: #ffffff !important;
  font-weight: 600 !important;
  -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stExpander"] summary svg {
  fill: #0AF0C8 !important;
}

/* GENERAL TEXT FALLBACK */
section[data-testid="stMain"] p,
section[data-testid="stMain"] li {
  color: rgba(255,255,255,0.75) !important;
}
section[data-testid="stMain"] h3,
[data-testid="stMarkdownContainer"] h3,
.stMarkdown h3 {
  color: #ffffff !important;
  background: transparent !important;
  -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stMain"] .caiq-result-title,
[data-testid="stMain"] h3 {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  background: transparent !important;
}
[data-testid="stMain"] h3.caiq-result-title {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  background: transparent !important;
}
[data-testid="stMain"] h3.caiq-result-title [data-testid="stHeaderActionElements"] {
  display: none !important;
}
[data-testid="stMain"] div[style*="border-left"],
[data-testid="stMain"] div[style*="rgba(61,110,255"],
[data-testid="stMain"] div[style*="rgba(61, 110, 255"] {
  color: rgba(255,255,255,0.85) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.85) !important;
}
section[data-testid="stMain"] h1,
section[data-testid="stMain"] h2,
section[data-testid="stMain"] h3,
section[data-testid="stMain"] strong {
  color: #ffffff !important;
}

/* RESULT CARDS */
.result-card {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 14px !important;
  padding: 20px 22px !important;
  margin-bottom: 12px !important;
  color: rgba(255,255,255,0.8) !important;
}
.result-card.top-option {
  border-color: rgba(10,240,200,0.25) !important;
  background: rgba(10,240,200,0.04) !important;
}
.result-card .meta,
.result-card .meta * {
  color: rgba(255,255,255,0.5) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.5) !important;
}
.result-card .insight-line,
.result-card .insight-line * {
  color: rgba(255,255,255,0.45) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.45) !important;
}
.result-card .card-link,
.result-card .card-link * {
  color: #0B1F3A !important;
  -webkit-text-fill-color: #0B1F3A !important;
}
.result-card h4,
.result-card .clamped-title {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  line-height: 1.3 !important;
  margin: 0 !important;
}
.card-head {
  display: flex !important;
  align-items: flex-start !important;
  justify-content: space-between !important;
  gap: 12px !important;
  margin-bottom: 10px !important;
}

/* SCORE PILL (Match 69%) */
.score-pill {
  background: rgba(10,240,200,0.1) !important;
  border: 1px solid rgba(10,240,200,0.3) !important;
  color: #0AF0C8 !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  padding: 3px 10px !important;
  border-radius: 100px !important;
  white-space: nowrap !important;
  flex-shrink: 0 !important;
}

/* TOP CHOICE */
.card-top-choice {
  display: inline-block !important;
  background: rgba(10,240,200,0.08) !important;
  border: 1px solid rgba(10,240,200,0.2) !important;
  color: #0AF0C8 !important;
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  padding: 3px 10px !important;
  border-radius: 100px !important;
  margin-bottom: 10px !important;
}

/* RANKING BADGES (Recomendación principal, Perfil más completo) */
.top-badge {
  display: inline-block !important;
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  color: rgba(255,255,255,0.6) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  padding: 3px 10px !important;
  border-radius: 100px !important;
}

/* STRATEGY BADGES */
.strategy-badge {
  display: inline-block !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  padding: 3px 10px !important;
  border-radius: 100px !important;
  margin: 2px !important;
}
.strategy-gap {
  background: rgba(255,77,106,0.1) !important;
  border: 1px solid rgba(255,77,106,0.25) !important;
  color: #FF6B85 !important;
}
.strategy-covered {
  background: rgba(61,110,255,0.1) !important;
  border: 1px solid rgba(61,110,255,0.25) !important;
  color: #6B9AFF !important;
}
.strategy-detected {
  background: rgba(61,110,255,0.1) !important;
  border: 1px solid rgba(61,110,255,0.25) !important;
  color: #6B9AFF !important;
}
.card-badge-row {
  margin-bottom: 10px !important;
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 6px !important;
}

/* META TEXT */
.card-metrics .meta {
  color: rgba(255,255,255,0.45) !important;
  font-size: 12px !important;
  line-height: 1.8 !important;
  white-space: pre-line !important;
}

/* INSIGHT LINE */
.insight-line {
  color: rgba(255,255,255,0.45) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.45) !important;
  font-size: 12px !important;
  font-style: italic !important;
  margin: 8px 0 12px !important;
  line-height: 1.6 !important;
}

/* CARD LINK */
.card-link {
  display: inline-block !important;
  background: #ffffff !important;
  border: 1px solid #bfdbfe !important;
  color: #0B1F3A !important;
  -webkit-text-fill-color: #0B1F3A !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  padding: 7px 16px !important;
  border-radius: 7px !important;
  text-decoration: none !important;
}
.card-link:hover {
  border-color: #60a5fa !important;
  color: #0B1F3A !important;
  -webkit-text-fill-color: #0B1F3A !important;
  background: #eff6ff !important;
}

/* RECENT JOB BADGE */
.badge-fast {
  background: rgba(255,180,0,0.1) !important;
  border: 1px solid rgba(255,180,0,0.25) !important;
  color: #FFB400 !important;
}

.result-card h3,
.result-card h4,
.result-card .card-title,
.result-card .clamped-title {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
.result-card .clamped-title,
.result-card .clamped-title span {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

</style>
""", unsafe_allow_html=True)

    # ── Render results ──────────────────────────────────────────────────────────
    render_role_fit_notice(rec, target_role, role_label)
    render_profile_summary_block(candidate_profile, candidate_skills, rec, role_label)
    render_quick_summary(jobs, rec)
    render_pdf_export_button(rec, candidate_profile, candidate_skills_explicit, role_label, target_role)
    render_skills_intelligence(candidate_skills_explicit, rec)
    render_skill_gap_radar(candidate_skills_explicit, rec, data, target_role, max_skills=8)
    render_recommendation_section_tabs(rec, jobs, data, live_price_map, target_role)


def inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Space+Grotesk:wght@600;700&family=Sora:wght@600;700;800&display=swap');
        #MainMenu, footer { visibility: hidden; }
        .block-container { padding-top: 0 !important; }
        :root {
          --bg-1: #f4f8ff;
          --bg-2: #e8f0ff;
          --ink: #0f172a;
          --muted: #475569;
          --brand: #1d4ed8;
          --brand-2: #0ea5e9;
          --card: #ffffff;
        }
        .stApp {
          font-family: 'Manrope', sans-serif;
          background: #060E1E !important;
          color: #ffffff;
        }
        /* Main content text contrast */
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h3,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h4 {
          color: #ffffff !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {
          background: linear-gradient(135deg, #0AF0C8 0%, #0ea5e9 100%) !important;
          color: #0a0f1e !important;
          border: none !important;
          font-weight: 700 !important;
          letter-spacing: 0.02em !important;
          border-radius: 10px !important;
          box-shadow: 0 4px 18px rgba(10,240,200,0.28) !important;
          transition: all .18s ease !important;
        }
        .stButton > button[kind="primary"]:hover {
          box-shadow: 0 6px 24px rgba(10,240,200,0.45) !important;
          transform: translateY(-1px) !important;
        }
        /* Dark text only for the teal-gradient primary CTA — NOT for "Ver más" */
        .stButton > button[kind="primary"]:not([disabled]) p,
        .stButton > button[kind="primary"]:not([disabled]) span,
        .stButton > button[data-testid="baseButton-primary"]:not([disabled]) p,
        .stButton > button[data-testid="baseButton-primary"]:not([disabled]) span {
          color: #0f172a !important;
        }
        .hero-wordmark {
          font-family: 'Sora', sans-serif;
          font-size: clamp(90px, 15vw, 180px);
          font-weight: 800;
          letter-spacing: -0.05em;
          line-height: 0.9;
          color: #ffffff;
          text-align: center;
          margin-bottom: 8px;
        }
        .hero-wordmark .q { color: #0AF0C8; }
        .acronym {
          font-size: 12px;
          letter-spacing: 0.15em;
          text-transform: uppercase;
          color: rgba(255,255,255,0.25);
          text-align: center;
          margin-bottom: 64px;
        }
        .hero-headline {
          font-size: clamp(22px, 3vw, 34px);
          font-weight: 700;
          color: #ffffff;
          text-align: center;
          line-height: 1.25;
          margin-bottom: 16px;
        }
        .hero-sub {
          font-size: 16px;
          color: rgba(255,255,255,0.4);
          text-align: center;
          max-width: 540px;
          margin: 0 auto 48px;
          line-height: 1.7;
        }
        /* Hero chips rendered as disabled Streamlit buttons */
        .stButton > button[disabled] {
          color: rgba(10,240,200,0.85) !important;
          opacity: 1 !important;
          border: 1px solid rgba(10,240,200,0.22) !important;
          background: rgba(10,240,200,0.06) !important;
          cursor: default !important;
          border-radius: 999px !important;
          font-size: 13px !important;
          font-weight: 500 !important;
        }
        .stButton > button[disabled] p,
        .stButton > button[disabled] span {
          color: rgba(10,240,200,0.85) !important;
        }
        html { scroll-behavior: smooth; }
        h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif; }
        /* Sidebar dark theme */
        [data-testid="stSidebar"] {
          background-color: #060E1E !important;
          border-right: 1px solid rgba(10,240,200,0.08) !important;
        }
        [data-testid="stSidebar"] * {
          color: #ffffff !important;
        }
        /* ── Section titles: PERFIL, FILTROS ── */
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] strong {
          color: #0AF0C8 !important;
          font-size: 11px !important;
          font-weight: 600 !important;
          letter-spacing: 0.2em !important;
          text-transform: uppercase !important;
        }

        /* ── Field labels: Language/Idioma, Rol objetivo, País... ── */
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label {
          color: rgba(255,255,255,0.55) !important;
          font-size: 12px !important;
        }
        [data-testid="stSidebar"] .block-container { padding-top: 1.1rem; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] .stNumberInput input {
          background-color: rgba(255,255,255,0.08) !important;
          border: 1px solid rgba(255,255,255,0.22) !important;
          border-radius: 8px !important;
          color: #fff !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="select"] div {
          color: #ffffff !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
          border-color: rgba(10,240,200,0.3) !important;
        }
        /* ── Selectbox selected value text (Español, Todos...) ── */
        [data-testid="stSidebar"] [data-baseweb="select"] span {
          color: #ffffff !important;
          font-size: 14px !important;
        }
        /* ── Checkbox label text ── */
        [data-testid="stSidebar"] [data-testid="stCheckbox"] p {
          color: rgba(255,255,255,0.6) !important;
          font-size: 13px !important;
          letter-spacing: 0 !important;
          text-transform: none !important;
        }
        [data-testid="stSidebar"] [data-testid="stSlider"] div[role="slider"] {
          background-color: #0AF0C8 !important;
        }
        /* ── Slider number labels (1595, 45549) ── */
        [data-testid="stSidebar"] [data-testid="stSlider"] p {
          color: rgba(255,255,255,0.35) !important;
          font-size: 11px !important;
          letter-spacing: 0 !important;
          text-transform: none !important;
        }
        [data-testid="stSidebarCollapseButton"] {
          color: rgba(10,240,200,0.6) !important;
        }
        [data-testid="stSidebar"]::-webkit-scrollbar {
          width: 4px;
        }
        [data-testid="stSidebar"]::-webkit-scrollbar-track {
          background: transparent;
        }
        [data-testid="stSidebar"]::-webkit-scrollbar-thumb {
          background: rgba(10,240,200,0.2);
          border-radius: 2px;
        }
        .hero-shell {
          position: relative;
          margin-top: 20px;
          margin-bottom: 20px;
          border-radius: 20px;
          padding: 64px 32px 72px 32px;
          min-height: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          background:
            radial-gradient(circle at 20% 20%, rgba(34,211,238,.16), transparent 38%),
            radial-gradient(circle at 82% 12%, rgba(34,211,238,.14), transparent 32%),
            linear-gradient(180deg, #020617 0%, #0f172a 100%);
          border: 1px solid rgba(34,211,238,.22);
          box-shadow: 0 12px 30px rgba(2,6,23,.45), inset 0 1px 0 rgba(148,163,184,.12);
          overflow: hidden;
          isolation: isolate;
        }
        .hero-shell::before {
          content: "";
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(148,163,184,.10) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148,163,184,.10) 1px, transparent 1px);
          background-size: 32px 32px;
          opacity: .16;
          z-index: -1;
        }
        .hero-shell::after {
          content: "";
          position: absolute;
          width: 360px;
          height: 360px;
          right: -110px;
          bottom: -190px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(34,211,238,.24) 0%, rgba(34,211,238,0) 72%);
          z-index: -1;
        }
        .hero-box {
          max-width: 940px;
          margin: 0 auto;
          border-radius: 16px;
          padding: 0;
          background: transparent;
          color: white;
          box-shadow: none;
          animation: none;
          position: relative;
          overflow: hidden;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .logo-block {
          display: flex;
          justify-content: center;
          align-items: center;
          margin-top: 6px;
          margin-bottom: 8px;
          width: 100%;
        }
        .logo {
          margin: 0;
          text-align: center;
          font-family: "Sora", "Space Grotesk", "Inter", sans-serif;
          font-size: clamp(100px, 18vw, 200px);
          font-weight: 800;
          letter-spacing: -0.06em;
          line-height: 0.9;
          text-transform: uppercase;
        }
        .logo-cai { color: #FFFFFF !important; }
        .logo-q {
          color: #0AF0C8 !important;
          position: relative;
          display: inline-block;
        }
        .logo-q::after {
          content: "Q";
          position: absolute;
          left: 0;
          top: 0;
          color: #0AF0C8;
          filter: blur(24px);
          opacity: .25;
          pointer-events: none;
        }
        .hero-kicker {
          display: inline-block;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.2em;
          color: rgba(10,240,200,.7);
          margin-bottom: 24px;
          font-weight: 600;
          border: 1px solid rgba(10,240,200,.2);
          border-radius: 999px;
          padding: 6px 18px;
          background: rgba(15,23,42,.55);
        }
        .tagline {
          margin: 0 0 40px 0;
          font-size: 13px;
          letter-spacing: 0.12em;
          color: rgba(255,255,255,.25);
          text-transform: uppercase;
        }
        .text-block {
          width: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .hero-title {
          margin: 0 auto 20px auto;
          font-size: clamp(22px, 3vw, 36px);
          font-weight: 700;
          max-width: 640px;
          color: #ffffff;
          text-align: center;
          letter-spacing: -0.02em;
          line-height: 1.2;
        }
        .hero-subtitle {
          margin: 0 auto 30px auto;
          font-size: 16px;
          max-width: 520px;
          color: rgba(255,255,255,.4);
          line-height: 1.7;
        }
        .hero-badges { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; max-width: 920px; margin: 0 auto 10px auto; }
        .hero-badges span {
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(255,255,255,0.03);
          color: rgba(255,255,255,.5);
          border-radius: 999px;
          font-size: 13px;
          font-weight: 400;
          padding: 8px 18px;
        }
        @keyframes riseIn {
          from { transform: translateY(6px); opacity: 0.2; }
          to { transform: translateY(0); opacity: 1; }
        }
        .chips-wrap { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
        .flow-strip-wrap {
          border-radius: 14px;
          padding: 10px 12px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(10,240,200,0.12);
          margin-bottom: 14px;
        }
        .flow-strip-title {
          color: rgba(10,240,200,0.6);
          font-size: .74rem;
          text-transform: uppercase;
          letter-spacing: .10em;
          font-weight: 700;
          margin-bottom: 7px;
        }
        .flow-strip {
          display: grid; grid-template-columns: repeat(3, minmax(120px, 1fr)); gap: 10px; margin-bottom: 14px;
        }
        .flow-step {
          border-radius: 10px; padding: 8px 10px;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.09);
          color: rgba(255,255,255,0.75); font-weight: 600; text-align: center;
          font-size: .9rem;
        }
        .quick-grid {
          display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 10px; margin-bottom: 12px;
        }
        .quick-card {
          border-radius: 12px; padding: 10px 12px;
          background: rgba(10,240,200,0.04);
          border: 1px solid rgba(10,240,200,0.14);
          box-shadow: 0 2px 12px rgba(0,0,0,0.18);
        }
        .quick-label { color: rgba(10,240,200,0.55); font-size: 0.76rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 700; }
        .quick-value { color: #ffffff; font-size: 0.94rem; font-weight: 700; margin-top: 4px; line-height: 1.35; }
        .skill-chip {
          background: rgba(139,92,246,0.15); color: #c4b5fd !important; border: 1px solid rgba(139,92,246,0.35); border-radius: 999px;
          padding: 5px 11px; font-size: 0.84rem; font-weight: 600;
          -webkit-text-fill-color: #c4b5fd !important;
        }
        .skill-chip.detected { background: rgba(10,240,200,0.12); border-color: rgba(10,240,200,0.35); color: #0AF0C8 !important; -webkit-text-fill-color: #0AF0C8 !important; }
        .skill-chip.missing { background: rgba(255,77,106,0.12); border-color: rgba(255,77,106,0.35); color: #FF6B85 !important; -webkit-text-fill-color: #FF6B85 !important; }
        .skill-chip.covered { background: rgba(37,99,235,0.16); border-color: rgba(96,165,250,0.45); color: #93C5FD !important; -webkit-text-fill-color: #93C5FD !important; }
        .skill-chip.neutral { background: rgba(139,92,246,0.15); border-color: rgba(139,92,246,0.35); color: #c4b5fd !important; -webkit-text-fill-color: #c4b5fd !important; }
        .result-card {
          background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
          padding: 13px 13px 12px 13px; margin-bottom: 12px;
          transition: transform .15s ease;
        }
        .result-card.compact {
          min-height: 336px;
          display: flex;
          flex-direction: column;
          justify-content: flex-start;
        }
        .result-card.top-option {
          border-color: #93c5fd;
          box-shadow: 0 10px 22px rgba(37,99,235,0.14);
          position: relative;
        }
        .result-card.top-option:before {
          content: "";
          position: absolute;
          left: 0;
          right: 0;
          top: 0;
          height: 3px;
          border-radius: 16px 16px 0 0;
          background: linear-gradient(90deg, #38bdf8 0%, #2563eb 100%);
        }
        .card-top-choice {
          display: inline-block;
          margin-bottom: 5px;
          border-radius: 999px;
          padding: 2px 8px;
          font-size: .68rem;
          font-weight: 800;
          background: #eff6ff;
          color: #1e3a8a;
          border: 1px solid #bfdbfe;
        }
        .result-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 16px 36px rgba(10,240,200,0.10), 0 4px 12px rgba(0,0,0,0.25);
          border-color: rgba(10,240,200,0.3);
          transition: all .18s ease;
        }
        .card-head {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          align-items: start;
          column-gap: 8px;
          min-height: 52px;
          margin-bottom: 4px;
        }
        .card-head h4 { margin: 0; color: #ffffff; }
        .clamped-title {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: normal;
          max-height: calc(2 * 1.28em);
          min-height: calc(2 * 1.28em);
          line-height: 1.28em;
          font-size: 0.93rem;
          font-weight: 700;
          padding-right: 0;
          max-width: 100%;
        }
        .card-badge-row { min-height: 22px; margin-bottom: 6px; }
        .card-metrics { min-height: 124px; }
        .meta { margin: 3px 0; color: rgba(255,255,255,0.5); font-size: 0.89rem; line-height: 1.28; }
        .meta.meta-block { white-space: pre-line; }
        .score-pill {
          position: static;
          justify-self: end;
          white-space: nowrap;
          background: rgba(10,240,200,0.1); color: #0AF0C8; border: 1px solid rgba(10,240,200,0.3);
          border-radius: 999px; padding: 3px 9px; font-size: 0.72rem; font-weight: 800;
        }
        .why-line {
          margin: 8px 0 0 0;
          color: rgba(255,255,255,0.7);
          font-size: .84rem;
          line-height: 1.4;
          background: rgba(10,240,200,0.05);
          border: 1px solid rgba(10,240,200,0.14);
          border-radius: 10px;
          padding: 8px 10px;
        }
        .card-link {
          display: inline-block; margin-top: 6px; text-decoration: none; font-weight: 700;
          color: rgba(255,255,255,0.65);
        }
        .card-link:hover { color: #0AF0C8; }
        .top-badge {
          display: inline-block;
          margin: 2px 0 3px 0;
          border-radius: 999px;
          padding: 1px 8px;
          font-size: .67rem;
          font-weight: 800;
          border: 1px solid transparent;
        }
        .top-badge.impact { background: rgba(255,77,106,0.1); color: #FF6B85; border-color: rgba(255,77,106,0.25); }
        .top-badge.fast { background: rgba(10,240,200,0.08); color: #0AF0C8; border-color: rgba(10,240,200,0.2); }
        .top-badge.complete { background: rgba(124,92,252,0.1); color: #BF9FFF; border-color: rgba(124,92,252,0.25); }
        .top-badge.balanced { background: rgba(61,110,255,0.1); color: #6B9AFF; border-color: rgba(61,110,255,0.25); }
        .top-badge[title] { cursor: help; }
        .strategy-badge {
          display: inline-block;
          margin: 1px 0 5px 0;
          border-radius: 999px;
          padding: 1px 8px;
          font-size: .67rem;
          font-weight: 800;
          border: 1px solid transparent;
        }
        .strategy-badge.strategy-direct { background: rgba(10,240,200,0.08); color: #0AF0C8; border-color: rgba(10,240,200,0.2); }
        .strategy-badge.strategy-gap { background: rgba(255,183,77,0.1); color: #FFB74D; border-color: rgba(255,183,77,0.25); }
        .strategy-badge.strategy-fast { background: rgba(124,92,252,0.1); color: #BF9FFF; border-color: rgba(124,92,252,0.25); }
        .strategy-badge.strategy-comp { background: rgba(61,110,255,0.1); color: #6B9AFF; border-color: rgba(61,110,255,0.25); }
        .strategy-badge.strategy-low { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.5); border-color: rgba(255,255,255,0.1); }
        .insight-line {
          margin: 8px 0 0 0;
          font-size: .83rem;
          line-height: 1.4;
          color: rgba(255,255,255,0.5) !important;
          -webkit-text-fill-color: rgba(255,255,255,0.5) !important;
          min-height: 2.55em;
          max-height: 2.88em;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .card-footer { margin-top: auto; padding-top: 7px; }
        .sticky-summary {
          position: sticky;
          top: 8px;
          z-index: 20;
          display: grid;
          grid-template-columns: 1.25fr 1fr;
          gap: 12px;
          border-radius: 16px;
          padding: 12px;
          margin: 6px 0 10px 0;
          background: linear-gradient(130deg, rgba(15,23,42,.95) 0%, rgba(30,58,138,.92) 100%);
          box-shadow: 0 8px 20px rgba(15,23,42,.25);
          border: 1px solid rgba(147,197,253,.35);
        }
        .ss-col {
          border-radius: 12px;
          padding: 10px 12px;
          background: rgba(255,255,255,.08);
          border: 1px solid rgba(191,219,254,.3);
        }
        .ss-col.recommended {
          background: rgba(14,165,233,.16);
          border: 1px solid rgba(125,211,252,.55);
          box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
        }
        .ss-label {
          color: #cbd5e1;
          text-transform: uppercase;
          letter-spacing: .06em;
          font-size: .72rem;
          font-weight: 800;
          margin-bottom: 4px;
        }
        .ss-value { color: #f8fafc; font-size: 1.02rem; font-weight: 800; }
        .ss-sub { color: #dbeafe; font-size: .84rem; margin-top: 2px; }
        .stTabs [data-baseweb="tab-list"] {
          gap: 6px;
          background: rgba(255,255,255,.55);
          padding: 6px;
          border-radius: 12px;
          border: 1px solid #dbeafe;
        }
        .stExpander summary {
          color: rgba(255,255,255,0.9) !important;
        }
        .stTabs [aria-selected="true"] {
          background: rgba(10,240,200,0.1) !important;
          color: #0AF0C8 !important;
        }
        /* Dark main content surfaces */
        [data-testid="stForm"],
        div[data-testid="stVerticalBlock"] > div {
          background-color: transparent !important;
        }
        [data-testid="stTabs"] button {
          background: rgba(255,255,255,0.04) !important;
          color: rgba(255,255,255,0.6) !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
          border-radius: 8px !important;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
          background: rgba(10,240,200,0.1) !important;
          color: #0AF0C8 !important;
          border-color: rgba(10,240,200,0.3) !important;
        }
        [data-testid="stAlert"],
        [data-testid="stInfo"] {
          background: rgba(10,240,200,0.05) !important;
          border: 1px solid rgba(10,240,200,0.15) !important;
          border-radius: 10px !important;
          color: rgba(255,255,255,0.7) !important;
        }
        .upload-shell {
          border-radius: 16px;
          padding: 20px 18px 16px;
          margin: 8px 0 14px 0;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(10,240,200,0.18);
          box-shadow: 0 6px 24px rgba(0,0,0,0.25);
        }
        .upload-title {
          color: #ffffff;
          font-weight: 800;
          font-size: .98rem;
          margin-bottom: 4px;
        }
        .upload-sub {
          color: rgba(255,255,255,0.45);
          font-size: .87rem;
          margin-bottom: 10px;
        }
        [data-testid="stFileUploader"] label,
        [data-testid="stTextArea"] label,
        [data-testid="stTextAreaLabel"] p {
          color: #ffffff !important;
          font-weight: 700 !important;
        }
        [data-testid="stFileUploaderDropzone"] {
          border-radius: 12px !important;
          border: 1px dashed #93c5fd !important;
          background: rgba(15,23,42,0.55) !important;
          padding-top: 10px !important;
          padding-bottom: 10px !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
          background: rgba(15,23,42,0.92) !important;
          color: #f8fafc !important;
          border: 1px solid rgba(10,240,200,0.35) !important;
        }
        [data-testid="stFileUploaderDropzone"] button:hover {
          border-color: rgba(10,240,200,0.6) !important;
          color: #ffffff !important;
        }
        [data-testid="stFileUploaderDropzone"] button p,
        [data-testid="stFileUploaderDropzone"] button span {
          color: #f8fafc !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] span {
          color: #e2e8f0 !important;
          font-weight: 700 !important;
        }
        /* Uploaded file row visibility */
        [data-testid="stFileUploaderFile"] {
          background: rgba(15,23,42,0.92) !important;
          border: 1px solid rgba(10,240,200,0.28) !important;
          border-radius: 10px !important;
        }
        [data-testid="stFileUploaderFileName"],
        [data-testid="stFileUploaderFileData"],
        [data-testid="stFileUploaderDeleteBtn"] {
          color: #f8fafc !important;
        }
        .profile-summary {
          background: rgba(255,255,255,0.03) !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
          border-radius: 14px !important;
          padding: 28px 32px !important;
          margin: 24px 0 !important;
        }
        .ps-title {
          font-size: 13px !important;
          font-weight: 600 !important;
          color: #ffffff !important;
          margin-bottom: 20px !important;
        }
        .ps-grid {
          display: grid !important;
          grid-template-columns: 1fr 1fr !important;
          gap: 10px !important;
        }
        .ps-item {
          background: rgba(255,255,255,0.02) !important;
          border: 1px solid rgba(255,255,255,0.06) !important;
          border-radius: 10px !important;
          padding: 14px 16px !important;
        }
        .ps-label {
          font-size: 10px !important;
          letter-spacing: 0.15em !important;
          text-transform: uppercase !important;
          color: #0AF0C8 !important;
          margin-bottom: 6px !important;
          font-weight: 600 !important;
        }
        .ps-value {
          color: rgba(255,255,255,0.8) !important;
          font-size: 13px !important;
          font-weight: 500 !important;
          line-height: 1.5 !important;
        }
        /* Results panel readability on dark background */
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
          color: #0AF0C8 !important;
          font-size: 36px !important;
          font-weight: 800 !important;
          letter-spacing: -0.02em !important;
        }
        [data-testid="stMetric"] [data-testid="stMetricLabel"] {
          color: rgba(255,255,255,0.45) !important;
          font-size: 10px !important;
          letter-spacing: 0.14em !important;
          text-transform: uppercase !important;
        }
        [data-testid="stExpander"] {
          background: #0C1628 !important;
          border: 1px solid rgba(10,240,200,0.15) !important;
          border-radius: 12px !important;
        }
        [data-testid="stExpander"] > div,
        [data-testid="stExpander"] > div > div,
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] details > div {
          background: #0C1628 !important;
        }
        [data-testid="stExpander"] summary {
          color: #ffffff !important;
          font-weight: 600 !important;
        }
        [data-testid="stTabs"] [role="tablist"] {
          background: rgba(255,255,255,0.03) !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
          border-radius: 10px !important;
          padding: 4px !important;
          gap: 4px !important;
        }
        [data-testid="stTabs"] [role="tab"] {
          background: transparent !important;
          color: rgba(255,255,255,0.65) !important;
          border: none !important;
          border-radius: 7px !important;
          font-size: 13px !important;
          font-weight: 500 !important;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
          background: rgba(10,240,200,0.12) !important;
          color: #0AF0C8 !important;
          border-bottom: 2px solid #0AF0C8 !important;
        }
        [data-testid="stTable"] table,
        .stDataFrame table {
          background: rgba(255,255,255,0.02) !important;
          border-radius: 10px !important;
          overflow: hidden !important;
        }
        [data-testid="stTable"] th,
        .stDataFrame th {
          background: rgba(10,240,200,0.08) !important;
          color: #0AF0C8 !important;
          font-size: 10px !important;
          letter-spacing: 0.15em !important;
          text-transform: uppercase !important;
          border: none !important;
        }
        [data-testid="stTable"] td,
        .stDataFrame td {
          color: rgba(255,255,255,0.8) !important;
          border-color: rgba(255,255,255,0.05) !important;
          background: transparent !important;
        }
        [data-testid="stAlert"][kind="success"],
        div[data-baseweb="notification"][kind="positive"] {
          background: rgba(10,240,200,0.08) !important;
          border: 1px solid rgba(10,240,200,0.25) !important;
          border-radius: 10px !important;
          color: #0AF0C8 !important;
        }
        [data-testid="stAlert"][kind="error"],
        div[data-baseweb="notification"][kind="negative"] {
          background: rgba(255,77,106,0.08) !important;
          border: 1px solid rgba(255,77,106,0.25) !important;
          border-radius: 10px !important;
          color: #FF4D6A !important;
        }
        [data-testid="stAlert"][kind="info"] {
          background: rgba(61,110,255,0.08) !important;
          border: 1px solid rgba(61,110,255,0.2) !important;
          border-radius: 10px !important;
          color: rgba(255,255,255,0.75) !important;
        }
        .stMarkdown code,
        [data-testid="stMarkdownContainer"] code {
          background: rgba(10,240,200,0.1) !important;
          color: #0AF0C8 !important;
          border: 1px solid rgba(10,240,200,0.2) !important;
          border-radius: 6px !important;
          padding: 2px 8px !important;
          font-size: 12px !important;
        }
        .score-pill {
          background: rgba(10,240,200,0.12) !important;
          color: #0AF0C8 !important;
          border: 1px solid rgba(10,240,200,0.3) !important;
        }
        /* Force readable white text in main content where captions/labels were too muted */
        [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] p,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stAppViewContainer"] [data-testid="stText"] {
          color: #ffffff !important;
        }
        [data-testid="stSpinner"] p,
        [data-testid="stSpinner"] span,
        [data-testid="stSpinner"] div {
          color: #ffffff !important;
        }
        .caiq-loading-overlay {
          position: fixed;
          inset: 0;
          background: rgba(3,8,17,0.58);
          backdrop-filter: blur(2px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          pointer-events: none;
        }
        .caiq-loading-modal {
          min-width: 340px;
          max-width: 540px;
          border-radius: 14px;
          padding: 20px 24px;
          background: linear-gradient(180deg, rgba(15,23,42,0.96), rgba(2,6,23,0.96));
          border: 1px solid rgba(10,240,200,0.30);
          box-shadow: 0 18px 48px rgba(0,0,0,0.45);
          text-align: center;
        }
        .caiq-loading-ring {
          width: 34px;
          height: 34px;
          border-radius: 50%;
          border: 3px solid rgba(10,240,200,0.20);
          border-top-color: #0AF0C8;
          margin: 0 auto 12px auto;
          animation: caiq-spin 0.9s linear infinite;
        }
        .caiq-loading-title {
          color: #ffffff;
          font-size: 16px;
          font-weight: 700;
          margin-bottom: 6px;
        }
        .caiq-loading-sub {
          color: rgba(255,255,255,0.75);
          font-size: 13px;
          letter-spacing: 0.02em;
        }
        @keyframes caiq-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @media (max-width: 760px) {
          .hero-shell { padding: 42px 14px 42px 14px; border-radius: 16px; min-height: 0; margin-top: 12px; margin-bottom: 12px; }
          .hero-kicker { margin-bottom: 16px; }
          .logo { font-size: clamp(72px, 24vw, 120px); letter-spacing: -0.04em; }
          .tagline { font-size: 12px; letter-spacing: .09em; margin-bottom: 24px; }
          .hero-title { font-size: 26px; margin-bottom: 14px; }
          .hero-subtitle { font-size: 14px; }
          .quick-grid, .flow-strip { grid-template-columns: 1fr; }
          [data-testid="stTabs"] [role="tab"] { font-size: 11px !important; padding: 4px 6px !important; }
          [data-testid="stTabs"] [role="tablist"] { gap: 2px !important; }
          .ps-grid { grid-template-columns: 1fr; }
          .sticky-summary { grid-template-columns: 1fr; position: static; }
          .result-card.compact { min-height: auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="CAIQ", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
    if "lang" not in st.session_state:
        st.session_state["lang"] = "es"

    def sidebar_section_title(text: str):
        st.sidebar.markdown(
            f"""
            <div style="
              color: #0AF0C8;
              font-size: 10px;
              font-weight: 600;
              letter-spacing: 0.22em;
              text-transform: uppercase;
              margin: 24px 0 8px 0;
              padding-bottom: 8px;
              border-bottom: 1px solid rgba(10,240,200,0.12);
            ">{escape(text)}</div>
            """,
            unsafe_allow_html=True,
        )

    def sidebar_field_label(text: str):
        st.sidebar.markdown(
            f"""
            <div style="
              color: rgba(255,255,255,0.4);
              font-size: 11px;
              letter-spacing: 0.08em;
              margin-bottom: 4px;
              margin-top: 16px;
            ">{escape(text)}</div>
            """,
            unsafe_allow_html=True,
        )

    sidebar_field_label("Language / Idioma")
    lang_label = st.sidebar.selectbox(
        "Language / Idioma",
        ["Español", "English"],
        index=0 if st.session_state["lang"] == "es" else 1,
        label_visibility="collapsed",
    )
    st.session_state["lang"] = "es" if lang_label == "Español" else "en"
    inject_styles()

    has_results = bool(st.session_state.get("caiq_generated_once", False))

    if not has_results:
        render_brand_header()
        render_flow_strip()

    tuned = load_tuned_config_only()
    data = load_data()
    wc = float(tuned.get("weight_coverage", 0.65))
    ws = float(tuned.get("weight_semantic", 0.35))

    role_map = {
        "Machine Learning Engineer": "ml_engineer",
        "Data Engineer": "data_engineer",
        "Data Scientist": "data_scientist",
        "Data Analyst": "data_analyst",
        "Other Data Role": "other_data_role",
    }

    sidebar_section_title(tr("profile"))
    sidebar_field_label(tr("target_role"))
    role_label = st.sidebar.selectbox(tr("target_role"), list(role_map.keys()), index=0, label_visibility="collapsed")
    target_role = role_map[role_label]

    sidebar_section_title(tr("filters"))
    masters_feat = data["masters_feat"].copy()
    if "price_comparable_eur" not in masters_feat.columns:
        masters_feat["price_comparable_eur"] = masters_feat.apply(comparable_master_price_eur, axis=1)
    prices = pd.to_numeric(masters_feat["price_comparable_eur"], errors="coerce").dropna()
    if prices.empty:
        min_price_available, max_price_available = 0, 15000
    else:
        # Use robust bounds to avoid extreme outliers stretching the slider.
        min_price_available = int(max(0, prices.quantile(0.05)))
        max_price_available = int(prices.quantile(0.95))
        max_price_available = max(max_price_available, min_price_available + 2000)

    sidebar_field_label(tr("enable_price"))
    use_price_filter = st.sidebar.checkbox(tr("enable_price"), value=False)
    include_no_price = st.sidebar.checkbox(tr("include_no_price"), value=True)
    sidebar_field_label(tr("price_range_comparable"))
    price_range = st.sidebar.slider(
        tr("price_range_comparable"),
        min_value=min_price_available,
        max_value=max_price_available,
        value=(min_price_available, max_price_available),
        step=250,
        disabled=not use_price_filter,
        label_visibility="collapsed",
    )
    min_price = float(price_range[0]) if use_price_filter else None
    max_price = float(price_range[1]) if use_price_filter else None
    if use_price_filter:
        st.sidebar.caption(tr("price_filtering", min=format_price_eur(min_price), max=format_price_eur(max_price)))
        st.sidebar.caption(tr("price_scope_note"))

    raw_locations = masters_feat["location"].dropna().astype(str).str.strip()
    location_df = pd.DataFrame({"location": raw_locations})
    location_df["country"] = location_df["location"].map(extract_country_from_location)
    # Fixed market scope for job recommendations.
    SUPPORTED_COUNTRIES = [
        "Spain",
        "Portugal",
        "France",
        "Italy",
        "Germany",
        "Netherlands",
        "Belgium",
        "United Kingdom",
        "Ireland",
        "United States",
        "Canada",
        "Mexico",
    ]
    COUNTRY_LABELS = {
        "Spain": "🇪🇸 España",
        "United States": "🇺🇸 Estados Unidos",
    }
    country_options = [tr("all_countries")] + [COUNTRY_LABELS.get(c, c) for c in SUPPORTED_COUNTRIES]
    sidebar_field_label(tr("country"))
    selected_country_label = st.sidebar.selectbox(tr("country"), country_options, index=0, label_visibility="collapsed")
    # Map display label → internal country string used in data
    _label_to_country = {v: k for k, v in COUNTRY_LABELS.items()}
    _label_to_country.update({c: c for c in SUPPORTED_COUNTRIES})
    selected_country = _label_to_country.get(selected_country_label, tr("all_countries"))

    if selected_country == tr("all_countries"):
        locality_values = sorted(location_df.loc[location_df["country"].isin(SUPPORTED_COUNTRIES), "location"].unique().tolist())
    else:
        locality_values = sorted(location_df.loc[location_df["country"] == selected_country, "location"].unique().tolist())
    sidebar_field_label(tr("city"))
    selected_locality = st.sidebar.selectbox(tr("city"), [tr("all_cities")] + locality_values[:200], index=0, label_visibility="collapsed")

    if selected_locality != tr("all_cities"):
        location = selected_locality
    elif selected_country != tr("all_countries"):
        location = selected_country
    else:
        location = ""

    suggested_keywords = ["AI", "Data Science", "Machine Learning", "Business Analytics", "Cloud", "Python", "SQL"]
    sidebar_field_label(tr("quick_keyword"))
    keyword_select = st.sidebar.selectbox(tr("quick_keyword"), [tr("none")] + suggested_keywords, index=0, label_visibility="collapsed")
    sidebar_field_label(tr("manual_keyword"))
    keyword_manual = st.sidebar.text_input(tr("manual_keyword"), value="", placeholder=tr("manual_placeholder"), label_visibility="collapsed")
    study_keyword = keyword_manual.strip() if keyword_manual.strip() else ("" if keyword_select == tr("none") else keyword_select)

    jobs_for_filters = data["jobs_feat"].copy()
    if "sector" in jobs_for_filters.columns:
        sector_vals = sorted([s for s in jobs_for_filters["sector"].dropna().astype(str).unique().tolist() if s and s.lower() != "other"])
    else:
        sector_vals = []
    sidebar_field_label(tr("sector_filter"))
    selected_sector = st.sidebar.selectbox(tr("sector_filter"), [tr("any_option")] + sector_vals, index=0, label_visibility="collapsed")

    if "seniority" in jobs_for_filters.columns:
        seniority_vals = sorted([s for s in jobs_for_filters["seniority"].dropna().astype(str).unique().tolist() if s and s.lower() != "unknown"])
    else:
        seniority_vals = []
    sidebar_field_label(tr("seniority_filter"))
    selected_seniority = st.sidebar.selectbox(tr("seniority_filter"), [tr("any_option")] + seniority_vals, index=0, label_visibility="collapsed")

    with st.sidebar.expander(tr("advanced_options")):
        use_live_course_price = st.checkbox(tr("live_price_beta"), value=True)
        st.caption(tr("live_price_note"))

    st.sidebar.caption(tr("weights", wc=f"{wc:.2f}", ws=f"{ws:.2f}"))

    if not has_results:
        st.markdown('<div id="cv-upload-anchor"></div><div id="cv-upload-section"></div>', unsafe_allow_html=True)
        st.markdown(f"<div class='upload-shell'><div class='upload-title'>{escape(tr('upload_card_title'))}</div><div class='upload-sub'>{escape(tr('upload_hint'))}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#ffffff;font-weight:800;font-size:1.05rem;margin:4px 0 8px 0;'>{escape(tr('cv_title'))}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#ffffff;font-size:.92rem;margin:0 0 6px 0;'>{escape(tr('upload_cv'))}</div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(tr("upload_cv"), type=["pdf", "docx", "txt"], label_visibility="collapsed")
        st.markdown(f"<div style='color:#ffffff;font-size:.92rem;margin:8px 0 6px 0;'>{escape(tr('paste_cv'))}</div>", unsafe_allow_html=True)
        cv_text = st.text_area(tr("paste_cv"), height=200, placeholder=tr("paste_placeholder"), label_visibility="collapsed")
        run_btn = st.button(tr("generate"), type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        uploaded_file = None
        cv_text = ""
        run_btn = st.button(tr("generate"), type="primary", use_container_width=False)

    model_path = ETL_DIR / "pipelines" / "build_datapath_model_advanced.py"
    model_version = model_path.stat().st_mtime if model_path.exists() else 0.0
    mod = load_model_module(model_version)
    catalog_emb = get_catalog_embeddings(mod, data)
    # Warm-up: pre-compila funciones NLP en el primer render (no en cada rerun)
    warmup_nlp_pipeline(mod, data["taxonomy"])

    if run_btn:
        loading_overlay = st.empty()
        with loading_overlay:
            render_loading_screen()
        try:
            if uploaded_file is None and not cv_text.strip():
                st.error(tr("need_cv"))
                return

            resume_text = cv_text.strip()
            uploaded_text = read_uploaded_cv(uploaded_file, mod)
            if uploaded_text:
                resume_text = uploaded_text
            elif uploaded_file is not None and not resume_text:
                st.error(tr("cv_extract_error"))
                return

            candidate_profile_new = mod.build_candidate_profile_hybrid(resume_text, data["taxonomy"])
            st.session_state["caiq_resume_text"] = resume_text
            st.session_state["caiq_candidate_profile"] = candidate_profile_new
            st.session_state["caiq_candidate_name"] = extract_candidate_name(resume_text)
            st.session_state["caiq_generated_once"] = True
            st.session_state.pop("caiq_reco_cache", None)
        finally:
            loading_overlay.empty()
        if st.session_state.get("caiq_generated_once"):
            st.rerun()

    candidate_profile = st.session_state.get("caiq_candidate_profile")
    if not candidate_profile:
        return

    candidate_skills = set(candidate_profile.get("skills_detected", []))
    candidate_skills_explicit = set(candidate_profile.get("skills_detected_explicit", []))
    if not candidate_skills_explicit and not (candidate_profile.get("inferred_skills", []) or []):
        candidate_skills_explicit = set(candidate_skills)

    filtered_masters = data["masters_feat"].copy()
    if min_price is not None:
        if "price_comparable_eur" not in filtered_masters.columns:
            filtered_masters["price_comparable_eur"] = filtered_masters.apply(comparable_master_price_eur, axis=1)
        comp = pd.to_numeric(filtered_masters["price_comparable_eur"], errors="coerce")
        in_range = comp.between(float(min_price), float(max_price), inclusive="both")
        if include_no_price:
            in_range = in_range | comp.isna()
        filtered_masters = filtered_masters[in_range].copy()

    filtered_jobs_feat = data["jobs_feat"].copy()
    # Restrict job recommendations to supported markets always,
    # regardless of country filter — market signal still uses full dataset.
    def _country_of(loc: str) -> str:
        return extract_country_from_location(str(loc or ""))
    _jf_countries = filtered_jobs_feat["location"].map(_country_of)
    _supported_mask = _jf_countries.isin(SUPPORTED_COUNTRIES)
    if _supported_mask.any():
        filtered_jobs_feat = filtered_jobs_feat[_supported_mask].copy()

    geo_country_used = ""
    geo_is_fallback = False
    location_filter_for_model = location

    if selected_locality != tr("all_cities"):
        filtered_masters = filtered_masters[
            filtered_masters["location"].fillna("").str.contains(selected_locality, case=False, na=False)
        ]
        filtered_jobs_feat = filtered_jobs_feat[
            filtered_jobs_feat["location"].fillna("").str.contains(selected_locality, case=False, na=False)
        ]
        geo_country_used = selected_locality
        location_filter_for_model = selected_locality
    elif selected_country != tr("all_countries"):
        filtered_masters, filtered_jobs_feat, geo_country_used, geo_is_fallback = apply_country_fallback(
            selected_country=selected_country,
            masters_df=filtered_masters,
            jobs_df=filtered_jobs_feat,
            target_role=target_role,
        )
        # Already pre-filtered by selected/fallback country.
        location_filter_for_model = ""
        if geo_country_used:
            if geo_is_fallback:
                render_result_notice(
                    tr("geo_fallback", requested=selected_country, country=geo_country_used),
                    tone="warning",
                )
            else:
                render_result_notice(tr("geo_used", country=geo_country_used), tone="info")

    filtered_jobs_feat, job_pref_msgs = apply_job_preference_fallback(
        filtered_jobs_feat,
        selected_sector=selected_sector,
        selected_seniority=selected_seniority,
    )
    for msg in job_pref_msgs:
        render_result_notice(msg, tone="info")

    reco_cache_key = _stable_hash(
        {
            "target_role": target_role,
            "candidate_profile": candidate_profile,
            "min_price": min_price,
            "max_price": max_price,
            "include_no_price": bool(include_no_price),
            "location_filter_for_model": location_filter_for_model,
            "study_keyword": study_keyword,
            "selected_sector": selected_sector,
            "selected_seniority": selected_seniority,
            "wc": float(wc),
            "ws": float(ws),
            "model_version": float(model_version),
            "jobs_count_filtered": int(len(filtered_jobs_feat)),
            "masters_count_filtered": int(len(filtered_masters)),
            "use_live_course_price": bool(use_live_course_price),
        }
    )
    cache_payload = st.session_state.get("caiq_reco_cache")

    if cache_payload and cache_payload.get("key") == reco_cache_key:
        rec = cache_payload["rec"]
        jobs = cache_payload["jobs"]
        stage_label = cache_payload["stage_label"]
        jobs_notice_key = cache_payload.get("jobs_notice_key")
        live_price_map = cache_payload.get("live_price_map", {})
    else:
        live_price_map = {}  # initialised here; populated later if live pricing enabled
        compute_ctx = nullcontext()
        compute_overlay = st.empty() if run_btn else None
        if compute_overlay is not None:
            with compute_overlay:
                render_loading_screen()
        try:
            with compute_ctx:
                rec = mod.recommend_learning_path(
                    candidate_skills=candidate_skills,
                    target_role=target_role,
                    role_skill_demand=data["role_skill_demand"],
                    masters_feat=filtered_masters,
                    master_skills=data["master_skills"],
                    courses_feat=data["courses_feat"],
                    course_skills=data["course_skills"],
                    filters={"max_price": max_price, "location": location_filter_for_model, "study_keyword": study_keyword},
                    weight_coverage=wc,
                    weight_semantic=ws,
                    master_reranker_model=None,
                    candidate_profile=candidate_profile,
                    taxonomy=data["taxonomy"],
                    catalog_embeddings=catalog_emb,
                )

                readiness = assess_job_readiness(candidate_profile, target_role=target_role)
                stage_key_map = {
                    "no_base": "readiness_no_base",
                    "base": "readiness_base",
                    "bridge": "readiness_bridge",
                    "ready": "readiness_ready",
                }
                stage_label = tr(stage_key_map.get(readiness.get("stage", "no_base"), "readiness_no_base"))

            can_unlock_with_path = (
                bool(candidate_profile.get("has_data_related_master", False))
                and str(readiness.get("stage", "no_base")) in {"bridge", "ready"}
                and int(readiness.get("technical_verified", 0) or 0) >= 2
                and float(rec.get("gap_coverage_ratio", 0.0) or 0.0) >= 0.75
            )
            can_unlock_with_score = (
                float(rec.get("role_match_score_current", 0.0) or 0.0) >= 60.0
                and bool(candidate_profile.get("has_data_related_master", False))
                and int(readiness.get("technical_verified", 0) or 0) >= 1
                and (bool(readiness.get("has_python", False)) or bool(readiness.get("has_sql", False)))
            )

            jobs_notice_key = None
            if readiness.get("eligible", False):
                jobs = mod.recommend_jobs(
                    target_role,
                    rec.get("final_skill_set", candidate_skills),
                    filtered_jobs_feat,
                    data["job_skills"],
                    candidate_profile=candidate_profile,
                )
            elif can_unlock_with_path or can_unlock_with_score:
                jobs = mod.recommend_jobs(
                    target_role,
                    rec.get("final_skill_set", candidate_skills),
                    filtered_jobs_feat,
                    data["job_skills"],
                    candidate_profile=candidate_profile,
                )
                jobs_notice_key = "jobs_unlocked_with_path"
            else:
                jobs = pd.DataFrame()
                jobs_notice_key = "jobs_blocked_non_data"

            if jobs_notice_key:
                render_result_notice(tr(jobs_notice_key), tone="info")

            st.session_state["caiq_reco_cache"] = {
                "key": reco_cache_key,
                "rec": rec,
                "jobs": jobs,
                "stage_label": stage_label,
                "jobs_notice_key": jobs_notice_key,
                "live_price_map": live_price_map,
            }

        except Exception as e:
            st.error(f"Error al generar recomendaciones: {e}")
        finally:
            if compute_overlay is not None:
                compute_overlay.empty()

    # \u2500\u2500 Render results panel from session state \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    _cache = st.session_state.get("caiq_reco_cache")
    if _cache:
        # Re-render notice on cache-hit (Streamlit rerenders don't re-run the else branch)
        _notice_key = _cache.get("jobs_notice_key")
        if _notice_key:
            render_result_notice(tr(_notice_key), tone="info")
        try:
            render_results_panel(
                rec=_cache["rec"],
                jobs=_cache["jobs"],
                role_label=role_label,
                candidate_skills_explicit=candidate_skills_explicit,
                candidate_profile=candidate_profile,
                candidate_skills=candidate_skills,
                data=data,
                live_price_map=_cache.get("live_price_map", {}),
                target_role=target_role,
                run_btn=False,
                stage_label=_cache.get("stage_label", ""),
            )
        except Exception as e:
            st.error(f"Error al renderizar resultados: {e}")


if __name__ == "__main__":
    main()
