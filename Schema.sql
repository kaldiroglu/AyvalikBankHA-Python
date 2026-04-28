--
-- PostgreSQL database dump
--

-- Command on the terminal:
-- pg_dump -U bankuser -h localhost -p 5432 -d ayvalikbank --schema-only --no-owner --no-privileges -f /Users/akin/Development/schema.sql

\restrict lc3D59Lu9Hr7wBerTxAIkzXqc4cABJRvvoS4D6e46HX6tsCDErQNFd3YJtpK5mF

-- Dumped from database version 18.3 (Postgres.app)
-- Dumped by pg_dump version 18.3 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.accounts (
    id uuid NOT NULL,
    balance numeric(19,2) NOT NULL,
    currency character varying(255) NOT NULL,
    owner_id uuid NOT NULL,
    status character varying(10) NOT NULL,
    interest_rate numeric(10,6),
    last_accrual_date date,
    matured boolean,
    maturity_date date,
    opened_on date,
    overdraft_limit numeric(19,2),
    principal numeric(19,2),
    type character varying(16) NOT NULL
);


--
-- Name: customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customers (
    id uuid NOT NULL,
    current_password character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    role character varying(255) NOT NULL,
    tier character varying(16) DEFAULT 'STANDARD'::character varying NOT NULL
);


--
-- Name: password_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_history (
    id uuid NOT NULL,
    hashed_password character varying(255) NOT NULL,
    "position" integer NOT NULL,
    customer_id uuid NOT NULL
);


--
-- Name: settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.settings (
    key character varying(255) NOT NULL,
    value character varying(255) NOT NULL
);


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transactions (
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    amount numeric(19,2) NOT NULL,
    currency character varying(255) NOT NULL,
    description character varying(255),
    "timestamp" timestamp(6) without time zone NOT NULL,
    type character varying(255) NOT NULL
);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: password_history password_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_history
    ADD CONSTRAINT password_history_pkey PRIMARY KEY (id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (key);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: customers ukrfbvkrffamfql7cjmen8v976v; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT ukrfbvkrffamfql7cjmen8v976v UNIQUE (email);


--
-- Name: password_history fk67sjutnh8tm8kn44uau6hnlkw; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_history
    ADD CONSTRAINT fk67sjutnh8tm8kn44uau6hnlkw FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- PostgreSQL database dump complete
--

\unrestrict lc3D59Lu9Hr7wBerTxAIkzXqc4cABJRvvoS4D6e46HX6tsCDErQNFd3YJtpK5mF

