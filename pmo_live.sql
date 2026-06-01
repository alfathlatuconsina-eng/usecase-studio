--
-- PostgreSQL database dump
--

\restrict Ru10fOb4OCA9JOmVRTguQ190T5QcoT73nbXQfG93JKyOfr3hc10HyqN8Rm0kje0

-- Dumped from database version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.people_evaluation DROP CONSTRAINT IF EXISTS people_evaluation_training_id_fkey;
ALTER TABLE IF EXISTS ONLY public.elibrary_documents DROP CONSTRAINT IF EXISTS elibrary_documents_subject_id_fkey;
ALTER TABLE IF EXISTS ONLY public.elibrary_documents DROP CONSTRAINT IF EXISTS elibrary_documents_category_id_fkey;
ALTER TABLE IF EXISTS ONLY public.elibrary_categories DROP CONSTRAINT IF EXISTS elibrary_categories_subject_id_fkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.quality_users DROP CONSTRAINT IF EXISTS quality_users_pkey;
ALTER TABLE IF EXISTS ONLY public.quality_users DROP CONSTRAINT IF EXISTS quality_users_email_key;
ALTER TABLE IF EXISTS ONLY public.quality_branches DROP CONSTRAINT IF EXISTS quality_branches_pkey;
ALTER TABLE IF EXISTS ONLY public.projects DROP CONSTRAINT IF EXISTS projects_pkey;
ALTER TABLE IF EXISTS ONLY public.people_users DROP CONSTRAINT IF EXISTS people_users_pkey;
ALTER TABLE IF EXISTS ONLY public.people_users DROP CONSTRAINT IF EXISTS people_users_email_key;
ALTER TABLE IF EXISTS ONLY public.people_training DROP CONSTRAINT IF EXISTS people_training_pkey;
ALTER TABLE IF EXISTS ONLY public.people_evaluation DROP CONSTRAINT IF EXISTS people_evaluation_pkey;
ALTER TABLE IF EXISTS ONLY public.people_certifications DROP CONSTRAINT IF EXISTS people_certifications_pkey;
ALTER TABLE IF EXISTS ONLY public.elibrary_users DROP CONSTRAINT IF EXISTS elibrary_users_pkey;
ALTER TABLE IF EXISTS ONLY public.elibrary_users DROP CONSTRAINT IF EXISTS elibrary_users_email_key;
ALTER TABLE IF EXISTS ONLY public.elibrary_subjects DROP CONSTRAINT IF EXISTS elibrary_subjects_pkey;
ALTER TABLE IF EXISTS ONLY public.elibrary_documents DROP CONSTRAINT IF EXISTS elibrary_documents_pkey;
ALTER TABLE IF EXISTS ONLY public.elibrary_categories DROP CONSTRAINT IF EXISTS elibrary_categories_pkey;
ALTER TABLE IF EXISTS ONLY public.audit_log DROP CONSTRAINT IF EXISTS audit_log_pkey;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.quality_users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.quality_branches ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.projects ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.people_users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.people_training ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.people_evaluation ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.people_certifications ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.elibrary_users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.elibrary_subjects ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.elibrary_documents ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.elibrary_categories ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.audit_log ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.quality_users_id_seq;
DROP TABLE IF EXISTS public.quality_users;
DROP SEQUENCE IF EXISTS public.quality_branches_id_seq;
DROP TABLE IF EXISTS public.quality_branches;
DROP SEQUENCE IF EXISTS public.projects_id_seq;
DROP TABLE IF EXISTS public.projects;
DROP SEQUENCE IF EXISTS public.people_users_id_seq;
DROP TABLE IF EXISTS public.people_users;
DROP SEQUENCE IF EXISTS public.people_training_id_seq;
DROP TABLE IF EXISTS public.people_training;
DROP SEQUENCE IF EXISTS public.people_evaluation_id_seq;
DROP TABLE IF EXISTS public.people_evaluation;
DROP SEQUENCE IF EXISTS public.people_certifications_id_seq;
DROP TABLE IF EXISTS public.people_certifications;
DROP SEQUENCE IF EXISTS public.elibrary_users_id_seq;
DROP TABLE IF EXISTS public.elibrary_users;
DROP SEQUENCE IF EXISTS public.elibrary_subjects_id_seq;
DROP TABLE IF EXISTS public.elibrary_subjects;
DROP SEQUENCE IF EXISTS public.elibrary_documents_id_seq;
DROP TABLE IF EXISTS public.elibrary_documents;
DROP SEQUENCE IF EXISTS public.elibrary_categories_id_seq;
DROP TABLE IF EXISTS public.elibrary_categories;
DROP SEQUENCE IF EXISTS public.audit_log_id_seq;
DROP TABLE IF EXISTS public.audit_log;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    ts timestamp without time zone NOT NULL,
    user_email character varying(255) NOT NULL,
    action character varying(20) NOT NULL,
    project_id integer,
    project_name character varying(255) NOT NULL,
    changes text NOT NULL
);


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: elibrary_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.elibrary_categories (
    id integer NOT NULL,
    subject_id integer NOT NULL,
    name character varying(160) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: elibrary_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.elibrary_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: elibrary_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.elibrary_categories_id_seq OWNED BY public.elibrary_categories.id;


--
-- Name: elibrary_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.elibrary_documents (
    id integer NOT NULL,
    subject_id integer NOT NULL,
    category_id integer NOT NULL,
    title character varying(255) NOT NULL,
    stored_name character varying(255) NOT NULL,
    original_name character varying(255) NOT NULL,
    size_bytes integer,
    uploaded_by character varying(255) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: elibrary_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.elibrary_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: elibrary_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.elibrary_documents_id_seq OWNED BY public.elibrary_documents.id;


--
-- Name: elibrary_subjects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.elibrary_subjects (
    id integer NOT NULL,
    name character varying(160) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: elibrary_subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.elibrary_subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: elibrary_subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.elibrary_subjects_id_seq OWNED BY public.elibrary_subjects.id;


--
-- Name: elibrary_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.elibrary_users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    pw_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: elibrary_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.elibrary_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: elibrary_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.elibrary_users_id_seq OWNED BY public.elibrary_users.id;


--
-- Name: people_certifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people_certifications (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    holder character varying(255) NOT NULL,
    cert_type character varying(80) NOT NULL,
    issue_date character varying(20) NOT NULL,
    expiry_date character varying(20) NOT NULL,
    status character varying(50) NOT NULL,
    notes text NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: people_certifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.people_certifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: people_certifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.people_certifications_id_seq OWNED BY public.people_certifications.id;


--
-- Name: people_evaluation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people_evaluation (
    id integer NOT NULL,
    training_id integer NOT NULL,
    reaction_score numeric,
    learning_score numeric,
    respondents integer,
    notes text NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: people_evaluation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.people_evaluation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: people_evaluation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.people_evaluation_id_seq OWNED BY public.people_evaluation.id;


--
-- Name: people_training; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people_training (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    category character varying(80) NOT NULL,
    method character varying(80) NOT NULL,
    organizer character varying(255) NOT NULL,
    date_start character varying(20) NOT NULL,
    date_end character varying(20) NOT NULL,
    target_pax integer,
    actual_pax integer,
    status character varying(50) NOT NULL,
    budget numeric,
    realization numeric,
    notes text NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: people_training_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.people_training_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: people_training_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.people_training_id_seq OWNED BY public.people_training.id;


--
-- Name: people_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people_users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    pw_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: people_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.people_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: people_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.people_users_id_seq OWNED BY public.people_users.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    sort integer NOT NULL,
    name character varying(255) NOT NULL,
    "group" character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    nature character varying(120) NOT NULL,
    "real" numeric,
    tl numeric,
    bo numeric,
    br numeric,
    target character varying(120) NOT NULL,
    orig character varying(120) NOT NULL,
    owner text NOT NULL,
    pm text NOT NULL,
    phase text NOT NULL,
    next_act text NOT NULL,
    risk text NOT NULL,
    stop text NOT NULL,
    reco text NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: quality_branches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quality_branches (
    id integer NOT NULL,
    period character varying(40) NOT NULL,
    period_label character varying(60) NOT NULL,
    branch character varying(160) NOT NULL,
    region character varying(80) NOT NULL,
    cs_score numeric,
    teller_score numeric,
    security_score numeric,
    intangible_score numeric,
    tangible_score numeric,
    overall_score numeric,
    status character varying(40) NOT NULL,
    notes text NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: quality_branches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.quality_branches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: quality_branches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.quality_branches_id_seq OWNED BY public.quality_branches.id;


--
-- Name: quality_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quality_users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    pw_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: quality_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.quality_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: quality_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.quality_users_id_seq OWNED BY public.quality_users.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    pw_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: elibrary_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_categories ALTER COLUMN id SET DEFAULT nextval('public.elibrary_categories_id_seq'::regclass);


--
-- Name: elibrary_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_documents ALTER COLUMN id SET DEFAULT nextval('public.elibrary_documents_id_seq'::regclass);


--
-- Name: elibrary_subjects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_subjects ALTER COLUMN id SET DEFAULT nextval('public.elibrary_subjects_id_seq'::regclass);


--
-- Name: elibrary_users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_users ALTER COLUMN id SET DEFAULT nextval('public.elibrary_users_id_seq'::regclass);


--
-- Name: people_certifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_certifications ALTER COLUMN id SET DEFAULT nextval('public.people_certifications_id_seq'::regclass);


--
-- Name: people_evaluation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_evaluation ALTER COLUMN id SET DEFAULT nextval('public.people_evaluation_id_seq'::regclass);


--
-- Name: people_training id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_training ALTER COLUMN id SET DEFAULT nextval('public.people_training_id_seq'::regclass);


--
-- Name: people_users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_users ALTER COLUMN id SET DEFAULT nextval('public.people_users_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: quality_branches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_branches ALTER COLUMN id SET DEFAULT nextval('public.quality_branches_id_seq'::regclass);


--
-- Name: quality_users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_users ALTER COLUMN id SET DEFAULT nextval('public.quality_users_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: audit_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_log (id, ts, user_email, action, project_id, project_name, changes) FROM stdin;
\.


--
-- Data for Name: elibrary_categories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.elibrary_categories (id, subject_id, name, created_at) FROM stdin;
1	1	Policies	2026-06-01 07:26:49.432103
2	1	Internal Memo	2026-06-01 07:26:49.432111
3	1	Technical Documents	2026-06-01 07:26:49.432114
4	2	Regulations	2026-06-01 07:26:49.436885
5	2	Circular Letters	2026-06-01 07:26:49.436893
6	2	Guidelines	2026-06-01 07:26:49.436895
7	3	SOPs	2026-06-01 07:26:49.43997
8	3	Work Instructions	2026-06-01 07:26:49.439979
9	3	Forms & Templates	2026-06-01 07:26:49.439981
10	4	IT Policies	2026-06-01 07:26:49.443535
11	4	Architecture	2026-06-01 07:26:49.443543
12	4	User Manuals	2026-06-01 07:26:49.443545
\.


--
-- Data for Name: elibrary_documents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.elibrary_documents (id, subject_id, category_id, title, stored_name, original_name, size_bytes, uploaded_by, created_at, updated_at) FROM stdin;
1	2	4	POJK LLD	2ed437085d1148df8adf7a80cad77be2.pdf	AI_Fluency_vocabulary_cheat_sheet.pdf	1501452	alfath@mncbank.co.id	2026-06-01 07:40:29.339185	2026-06-01 07:40:29.339191
\.


--
-- Data for Name: elibrary_subjects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.elibrary_subjects (id, name, created_at) FROM stdin;
1	Risk Management	2026-06-01 07:26:49.42818
2	Compliance	2026-06-01 07:26:49.434873
3	Operations	2026-06-01 07:26:49.438322
4	Information Technology	2026-06-01 07:26:49.441878
\.


--
-- Data for Name: elibrary_users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.elibrary_users (id, email, pw_hash, role, created_at) FROM stdin;
1	alfath@mncbank.co.id	$2b$12$FN3WFuOsgFzQjjE/Yv0WgeYB0I2UBGa2IpOC6BMY9ujjQmozckuQ2	super_admin	2026-06-01 07:26:49.408138
2	guest@mncbank.co.id	$2b$12$6pHG6mkkVQ8h2zzoAZSBM.YvHiVjjAoTecHJmPIMi6Zlq.KFoM.Gi	user	2026-06-01 08:48:35.17315
\.


--
-- Data for Name: people_certifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.people_certifications (id, name, holder, cert_type, issue_date, expiry_date, status, notes, created_at) FROM stdin;
1	OJK Risk Management Certification Level 1	Risk Management Group	Certification	2024-06-01	2026-06-01	Expiring	Mass renewal required for 15 staff.	2026-05-31 17:13:42.632015
2	PPATK AML/CFT Certification	Compliance Department	Certification	2025-04-07	2027-04-07	Active	Renewed after April 2026 training.	2026-05-31 17:13:42.632022
3	Bank Indonesia RTGS Operator License	Operations Group	License	2023-03-15	2026-03-15	Expired	Renewal pending resubmission to Bank Indonesia.	2026-05-31 17:13:42.632024
4	ISO 27001 Internal Auditor	IT Security / Risk	Certification	2024-09-01	2026-09-01	Active	Expires Sep 2026; renewal planned Q3 2026.	2026-05-31 17:13:42.632027
5	Monthly Regulatory Report (LBU) — OJK	Finance Group	Reporting	2026-05-01	2026-06-30	Active	Monthly deadline — June report due 30 Jun 2026.	2026-05-31 17:13:42.632029
6	Annual SKAI Internal Audit Report	Internal Audit	Reporting	2026-01-01	2026-12-31	Active	Annual submission to OJK.	2026-05-31 17:13:42.632031
7	PMP Certification — PMO Staff	PMO Team	Certification	2023-05-15	2026-05-15	Expired	3 staff expired May 2026; renewal PDUs in progress.	2026-05-31 17:13:42.632033
8	SWIFT Operator Certification	Treasury Operations	Certification	2024-11-01	2026-11-01	Active	Expiry Nov 2026; renewal reminder set for Aug 2026.	2026-05-31 17:13:42.632035
\.


--
-- Data for Name: people_evaluation; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.people_evaluation (id, training_id, reaction_score, learning_score, respondents, notes, created_at) FROM stdin;
1	1	4.2	78.5	28	Well received; content was relevant and practical.	2026-05-31 17:13:42.636709
2	2	4.5	82.0	18	Participants rated the hands-on exercises highly.	2026-05-31 17:13:42.636717
3	3	4.7	88.0	14	Excellent facilitator; all participants recommend repeat.	2026-05-31 17:13:42.636719
4	4	3.8	72.0	90	Content was mandatory; slightly dry but comprehensive.	2026-05-31 17:13:42.636721
5	5	4.6	85.5	9	High engagement; 7 out of 9 plan to take the PMP exam.	2026-05-31 17:13:42.636724
\.


--
-- Data for Name: people_training; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.people_training (id, name, category, method, organizer, date_start, date_end, target_pax, actual_pax, status, budget, realization, notes, created_at) FROM stdin;
1	Risk Management Fundamentals	Compliance	Classroom	OJK Institute	2026-01-20	2026-01-22	30	28	Completed	50	48.5	Annual compliance training for all risk staff.	2026-05-31 17:13:42.61975
2	Python for Data Analytics	Technical	Virtual	Digital Learning Hub	2026-02-10	2026-02-12	20	18	Completed	30	28	Introductory Python course for analyst team.	2026-05-31 17:13:42.619756
3	Leadership Excellence Program	Leadership	Classroom	HR Development	2026-03-03	2026-03-05	15	14	Completed	80	77.5	For mid-level managers.	2026-05-31 17:13:42.619757
4	AML/CFT Certification Refresher	Regulatory	E-Learning	PPATK	2026-04-07	2026-04-07	100	95	Completed	10	9.5	Mandatory annual AML/CFT refresher for compliance staff.	2026-05-31 17:13:42.619759
5	Project Management Professional (PMP) Prep	Technical	Virtual	PMI Indonesia	2026-05-05	2026-05-09	10	9	Completed	40	38	PMP exam preparation for PMO staff.	2026-05-31 17:13:42.61976
6	Digital Banking Innovation Summit	Soft Skills	Classroom	ISEI	2026-06-15	2026-06-16	25	\N	Planned	60	\N	Upcoming conference on digital banking trends.	2026-05-31 17:13:42.619761
7	Cybersecurity Awareness Training	Technical	E-Learning	IT Security Team	2026-07-01	2026-07-31	250	\N	Planned	15	\N	Annual mandatory cybersecurity awareness for all staff.	2026-05-31 17:13:42.619763
8	Communication & Presentation Skills	Soft Skills	Classroom	HR Development	2026-08-11	2026-08-12	20	\N	Planned	35	\N	Presentation skills for front-liners and analysts.	2026-05-31 17:13:42.619764
\.


--
-- Data for Name: people_users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.people_users (id, email, pw_hash, role, created_at) FROM stdin;
1	alfath@mncbank.co.id	$2b$12$FN3WFuOsgFzQjjE/Yv0WgeYB0I2UBGa2IpOC6BMY9ujjQmozckuQ2	admin	2026-05-31 18:32:19.345466
2	admin@mncbank.co.id	$2b$12$eo1qHYVr/HVjGIN67c417uaq9q5I2Y8T6IZqYkKAnLaslW2EzfC6e	viewer	2026-05-31 18:37:13.713104
3	guest@mncbank.co.id	$2b$12$LpCBbNjNNlDHRJ16MeKzJ.IPAoA/AsBv8Pr3v1aFIGjkYexGW8IDy	viewer	2026-05-31 18:37:32.677864
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.projects (id, sort, name, "group", status, nature, "real", tl, bo, br, target, orig, owner, pm, phase, next_act, risk, stop, reco, created_at) FROM stdin;
1	1	QRIS Acquiring	Business	In-Progress	Technology Dev.	91	100	100	66	02 Jun 2026	02 Mar'26	Digital Business / Digital Technology	Aditya Fatur / Naufal / Lilia	Submit dokumen & surat pernyataan ke Bank Indonesia; workshop FDS dengan tim MTN.	Workshop Technical FDS 03 Jun; set-up 04-05 Jun 2026.	Keterlambatan pemenuhan dokumen di beberapa kesempatan.	Kesalahan UAT (2025); assessment (Mar'26); kekurangan dokumen (Mei'26).	Telah dilakukan arrangement untuk percepatan set-up FDS.	2026-05-30 14:24:01.891419
2	2	API Management	Business	In-Progress	API Management	60	66.7	100	66	31 Jul 2026		Digital Business / Technology / Credit Card	Yudi Y / Bowie / David B / Donny A	UAT API On-Boarding; instalasi & assessment API Savings (22 API).	Pentest; tuning server; daftar SNAP BI.	Penjadwalan Pentest menyebabkan delivery mundur 1 pekan.	Kesalahan UAT (Des'25); assessment (Mar'26); dokumen (Mei'26).	Percepatan rekomendasi ASPI & izin paralel.	2026-05-30 14:24:01.891426
3	3	Konversi Valas ke Rupiah	Business	In-Progress	FX Conversion	93	100	\N	\N	04 Jun 2026	31 Mar'26	Treasury	Aditya Fatur / Purbayu	Deploy to Production 30 Apr'26; issue rekonsiliasi & spread harga.	Dokumen pelaporan OJK & BI; rekonsiliasi.	Dokumen ke regulator & BI belum disiapkan.	—	Mendorong kesiapan dokumen ke regulator.	2026-05-30 14:24:01.891427
4	4	Dormant Account Classification	Business	In-Progress	Core Banking	93	100	100	55	19 Jun 2026	01 Mei'26	Liabilities Product Development Group	Yani / Naufal / Imelda / Vita	SIT selesai; UAT tertunda (Dev environment dipakai Digital s/d 11 Jun).	Rekening saldo 0 ditutup otomatis; finalisasi timeline Silverlake.	UAT belum jalan akibat sharing resource.	—	Monitor timeline keseluruhan dengan Silverlake.	2026-05-30 14:24:01.891429
5	5	Data Center Migration	Non-Business	In-Progress	Infrastructure	95	100	100	88	25 Jun 2026	30 Apr'26	Technology Dir.	Yudi Y / Irfan Rifai / Bowie	Relokasi koneksi & perangkat dari MNC Tower Lt4; menunggu Telkom.	Percepatan procurement & PO.	Proses Telkom belum dapat dimonitor.	—	Komunikasi intensif dengan Telkom.	2026-05-30 14:24:01.89143
6	6	Fraud Detection System (FDS)	Non-Business	In-Progress	Fraud Detection	15	15.62	100	55	16 Jan 2027		Risk Management Group	Reza / Khabi / Michael Satrio	Finalisasi Field Mapping & Table Reference [03–05 Jun'26].	Formulasi TSD & FSD; diskusi Branch Field Mapping.	Risiko keterlambatan diskusi Table Activity; investigasi PTAP.	Finalisasi PKS oleh RMG; GBG menunggu Predator Config.	Monitoring agar timeline on-track.	2026-05-30 14:24:01.891431
7	7	OPICS	Non-Business	In-Progress	Treasury System	95	100	100	74	W1 Jun 2026	02 Apr	Treasury Group	Vicco / Purbayu / Ananda Dessi	Validasi & compile skenario 8 Jun; migrasi 09–12 Jun 2026.	Input transaksi; verify; migrasi & upgrade OPICS & GRIT.	Potensi selisih pembukuan saat parallel run.	Error BSIP saat EOD UAT (30 Apr) masih investigasi PTAP.	Monitoring hasil test rutin.	2026-05-30 14:24:01.891433
8	8	Enhancement RTGS	Non-Business	Completed	Automation	100	100	100	88	05 May 2026	30 Apr	Digital Business / IT Technology	Bowie / Rina M	RTGS naik production; re-deploy job handler 05 Mei.	Monitoring.	Data cleansing mungkin tidak signifikan turunkan CPU.	CPU tinggi akibat junk data 2025.	—	2026-05-30 14:24:01.891434
9	9	QRIS CPM	Non-Business	In-Progress	QRIS	75	100	\N	\N	W2 Jun 2026		Digital Business Group	Aditya Fatur / Bowie	Progress SIT; perlu Pentest & audit eksternal.	Go-Live W2 Juni.	Perlu persiapan dokumen ke regulator.	—	Percepatan ke ASPI/OJK/BI.	2026-05-30 14:24:01.891435
10	10	QRIS Credit Card	Non-Business	In-Progress	QRIS	75	75	\N	\N	W4 Jun 2026		Credit Card Group	Bowie	Done development Ascend; progress SIT.	Go-Live W2 Juni.	Belum siap dokumen ASPI; Pentest belum dijadwalkan.	—	Percepatan ke regulator.	2026-05-30 14:24:01.891436
11	11	EOD 24/7 (Night Mode)	Non-Business	In-Progress	Core Banking	5	4	\N	\N	10 Oct 2026		IT Group / Digital Business	Aditya Fatur / Naufal	Kick-off 14 Mei; development Silverlake sejak 18 Mei.	Penyusunan BRD; Core Development.	—	—	—	2026-05-30 14:24:01.891437
12	12	Revamp Website	Non-Business	Completed	Website Revamp	100	100	100	100	22 Apr 2026 (Live)	01 Apr'26	Corporate Secretary		Live-run per 22 Apr 2026; site accessible at https://mncbank.co.id/	Post Implementation Review (PIR).	—	—	—	2026-05-31 17:53:14.803524
13	13	TabMotion NTB WNA	Business	Completed	Digital Onboarding (WNA)	100	100	100	100	12 Nov 2025 (Go-Live)	31 Jan 2026	Digital Business Dir.		Dev/SIT/UAT/Regresi/PAT completed Oct'25; Go-Live 12 Nov'25.	Live to Appstore 12 Nov'25; Playstore 6 Nov'25.	—	—	—	2026-05-31 17:53:14.803532
14	14	GiroMotion ETB WNA	Business	Completed	Digital Onboarding (WNA)	100	100	100	100	18 Des 2025 (Go-Live)	31 Jan 2026	Digital Business Dir.		BRD→Live Nov-Des'25; Live to store 19 Des'25.	Go-Live 18 Des'25; reported to OJK & BI.	—	—	—	2026-05-31 17:53:14.803534
15	15	Secured Credit Card (Nasabah NTB)	Business	Completed	Credit Card	100	100	100	100	December 2025		Credit Card Group		Deploy to Production; Released APK/IPA 16 Des'25.	Enhancement Secure Card for ETB customers (BRD in progress).	—	—	—	2026-05-31 17:53:14.81006
16	16	EBIZZ Banking (Upgrade Database)	Non-Business	Completed	Infrastructure / Database	100	100	100	100	07 Feb 2026		IT Group		Upgrade DB & engine, tuning, bug-fixing; Stress/SIT/UAT in parallel.	Go-Live 7 Feb'26.	—	—	—	2026-05-31 17:53:14.810068
17	17	Call Center	Non-Business	Completed	Service / Operations	100	100	100	100	01 Sep 2025 (Go-Live)		Digital Business Dir.		UAT form fully approved; cost memo approved by BoD.	Go-Live 1 Sep 2025.	—	—	—	2026-05-31 17:53:14.810071
18	18	KRI Rating	Non-Business	Completed	Corporate Rating	100	100	100	100	20 Jun 2025		Financial Control / Corporate Secretary		Final KRI rating for MNC Bank: single 'A' rating.	—	—	—	—	2026-05-31 17:53:14.810073
19	19	RDN Institusi (eBIZ Banking)	Business	Completed	Product Development	100	100	100	100	10 Oct 2025 (Live)		Digital Business / IT Group		SIT/UAT/Regresi/PAT completed; LIVE 10 October 2025.	Reported to OJK.	—	—	—	2026-05-31 17:53:14.810076
\.


--
-- Data for Name: quality_branches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.quality_branches (id, period, period_label, branch, region, cs_score, teller_score, security_score, intangible_score, tangible_score, overall_score, status, notes, created_at) FROM stdin;
1	Period 35	Mar–Apr 2026	KC Sample Jakarta Pusat	Jabodetabek	94	92	90	92.9	91	92.6	Excellent	Strong cross-selling; lobby well maintained.	2026-05-31 20:14:41.558874
2	Period 35	Mar–Apr 2026	KC Sample Jakarta Selatan	Jabodetabek	90	88	86	88.9	89	88.9	Good	Good attitude; ATM area needs minor upkeep.	2026-05-31 20:14:41.558879
3	Period 35	Mar–Apr 2026	KCP Sample Bekasi	Jabodetabek	87	85	88	86.6	82	85.9	Good	Teller skill solid; promo media outdated.	2026-05-31 20:14:41.558881
4	Period 35	Mar–Apr 2026	KCP Sample Depok	Jabodetabek	83	80	84	82.3	78	81.7	Good	Toilet facility flagged for improvement.	2026-05-31 20:14:41.558883
5	Period 35	Mar–Apr 2026	KC Sample Bandung	Jawa Barat	91	89	87	89.9	90	89.9	Good	Consistent service standards.	2026-05-31 20:14:41.558884
6	Period 35	Mar–Apr 2026	KC Sample Surabaya	Jawa Timur	88	86	85	87.0	84	86.5	Good	Appearance excellent; FX underlying knowledge to improve.	2026-05-31 20:14:41.558885
7	Period 35	Mar–Apr 2026	KC Sample Medan	Sumatera	79	77	82	78.9	75	78.3	Needs Improvement	Below target; coaching on cross-selling scheduled.	2026-05-31 20:14:41.558886
8	Period 35	Mar–Apr 2026	KC Sample Palembang	Sumatera	85	83	86	84.6	81	84.1	Good	Security courteous; lobby layout improved.	2026-05-31 20:14:41.558887
9	Period 35	Mar–Apr 2026	KC Sample Pekanbaru	Sumatera	82	84	80	82.3	79	81.8	Good	Treasury product knowledge gap noted.	2026-05-31 20:14:41.558889
10	Period 35	Mar–Apr 2026	KCP Sample Jambi	Sumatera	76	74	78	75.7	72	75.1	Needs Improvement	Needs improvement across tangible facilities.	2026-05-31 20:14:41.55889
11	Period 35	Mar–Apr 2026	KC Sample Makassar	Indonesia Timur	89	87	88	88.3	86	88.0	Good	Digital onboarding explained clearly.	2026-05-31 20:14:41.558891
12	Period 35	Mar–Apr 2026	KC Sample Denpasar	Bali Nusra	92	90	91	91.3	93	91.6	Excellent	Top-tier facilities; strong frontliner attitude.	2026-05-31 20:14:41.558892
\.


--
-- Data for Name: quality_users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.quality_users (id, email, pw_hash, role, created_at) FROM stdin;
1	alfath@mncbank.co.id	$2b$12$FN3WFuOsgFzQjjE/Yv0WgeYB0I2UBGa2IpOC6BMY9ujjQmozckuQ2	admin	2026-05-31 20:14:41.540864
2	admin@mncbank.co.id	$2b$12$Ysdk0AGapajQg1xzjcfXYu8RbkpXKfQdqfsJyh5v.KIKd3mZ2t4Pq	editor	2026-06-01 05:59:19.843023
3	guest@mncbank.co.id	$2b$12$swDoJQVdTOTUIPKuUQyevej8L2eRIHSvYl2edA1VnoBTeirVgAPcK	viewer	2026-06-01 05:59:42.630777
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, pw_hash, role, created_at) FROM stdin;
1	alfath@mncbank.co.id	$2b$12$FN3WFuOsgFzQjjE/Yv0WgeYB0I2UBGa2IpOC6BMY9ujjQmozckuQ2	admin	2026-05-30 14:24:01.877966
2	admin@mncbank.co.id	$2b$12$Y4vuBlSKLFKqLbuPERtkz.T996GjulaI.z1xzoVcp54aN8TmJ7Nci	editor	2026-05-31 17:13:42.599211
3	guest@mncbank.co.id	$2b$12$G4OOURDE6M8B6RF5PwSdyOettw4U7EBRRTXT8ejf5r7Y3.O7sLzUW	viewer	2026-05-31 17:30:07.90569
\.


--
-- Name: audit_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_log_id_seq', 1, false);


--
-- Name: elibrary_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.elibrary_categories_id_seq', 12, true);


--
-- Name: elibrary_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.elibrary_documents_id_seq', 1, true);


--
-- Name: elibrary_subjects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.elibrary_subjects_id_seq', 4, true);


--
-- Name: elibrary_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.elibrary_users_id_seq', 2, true);


--
-- Name: people_certifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.people_certifications_id_seq', 8, true);


--
-- Name: people_evaluation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.people_evaluation_id_seq', 5, true);


--
-- Name: people_training_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.people_training_id_seq', 8, true);


--
-- Name: people_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.people_users_id_seq', 3, true);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.projects_id_seq', 19, true);


--
-- Name: quality_branches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.quality_branches_id_seq', 12, true);


--
-- Name: quality_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.quality_users_id_seq', 3, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: elibrary_categories elibrary_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_categories
    ADD CONSTRAINT elibrary_categories_pkey PRIMARY KEY (id);


--
-- Name: elibrary_documents elibrary_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_documents
    ADD CONSTRAINT elibrary_documents_pkey PRIMARY KEY (id);


--
-- Name: elibrary_subjects elibrary_subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_subjects
    ADD CONSTRAINT elibrary_subjects_pkey PRIMARY KEY (id);


--
-- Name: elibrary_users elibrary_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_users
    ADD CONSTRAINT elibrary_users_email_key UNIQUE (email);


--
-- Name: elibrary_users elibrary_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_users
    ADD CONSTRAINT elibrary_users_pkey PRIMARY KEY (id);


--
-- Name: people_certifications people_certifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_certifications
    ADD CONSTRAINT people_certifications_pkey PRIMARY KEY (id);


--
-- Name: people_evaluation people_evaluation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_evaluation
    ADD CONSTRAINT people_evaluation_pkey PRIMARY KEY (id);


--
-- Name: people_training people_training_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_training
    ADD CONSTRAINT people_training_pkey PRIMARY KEY (id);


--
-- Name: people_users people_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_users
    ADD CONSTRAINT people_users_email_key UNIQUE (email);


--
-- Name: people_users people_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_users
    ADD CONSTRAINT people_users_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: quality_branches quality_branches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_branches
    ADD CONSTRAINT quality_branches_pkey PRIMARY KEY (id);


--
-- Name: quality_users quality_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_users
    ADD CONSTRAINT quality_users_email_key UNIQUE (email);


--
-- Name: quality_users quality_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_users
    ADD CONSTRAINT quality_users_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: elibrary_categories elibrary_categories_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_categories
    ADD CONSTRAINT elibrary_categories_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.elibrary_subjects(id) ON DELETE CASCADE;


--
-- Name: elibrary_documents elibrary_documents_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_documents
    ADD CONSTRAINT elibrary_documents_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.elibrary_categories(id) ON DELETE CASCADE;


--
-- Name: elibrary_documents elibrary_documents_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.elibrary_documents
    ADD CONSTRAINT elibrary_documents_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.elibrary_subjects(id) ON DELETE CASCADE;


--
-- Name: people_evaluation people_evaluation_training_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people_evaluation
    ADD CONSTRAINT people_evaluation_training_id_fkey FOREIGN KEY (training_id) REFERENCES public.people_training(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Ru10fOb4OCA9JOmVRTguQ190T5QcoT73nbXQfG93JKyOfr3hc10HyqN8Rm0kje0

