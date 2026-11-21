BEGIN;

--
-- ACTION CREATE TABLE
--
CREATE TABLE "agent_session" (
    "id" bigserial PRIMARY KEY,
    "task" text NOT NULL,
    "status" text NOT NULL,
    "modelName" text NOT NULL,
    "provider" text NOT NULL,
    "isLocal" boolean NOT NULL,
    "route" text NOT NULL,
    "outcome" text,
    "answer" text,
    "startedAt" timestamp without time zone NOT NULL,
    "updatedAt" timestamp without time zone NOT NULL,
    "stepCount" bigint NOT NULL
);

-- Indexes
CREATE INDEX "agent_session_started_idx" ON "agent_session" USING btree ("startedAt");

--
-- ACTION CREATE TABLE
--
CREATE TABLE "agent_step" (
    "id" bigserial PRIMARY KEY,
    "sessionId" bigint NOT NULL,
    "index" bigint NOT NULL,
    "kind" text NOT NULL,
    "title" text NOT NULL,
    "detail" text NOT NULL,
    "durationMs" bigint NOT NULL,
    "createdAt" timestamp without time zone NOT NULL
);

-- Indexes
CREATE UNIQUE INDEX "agent_step_session_index_idx" ON "agent_step" USING btree ("sessionId", "index");

--
-- ACTION CREATE FOREIGN KEY
--
ALTER TABLE ONLY "agent_step"
    ADD CONSTRAINT "agent_step_fk_0"
    FOREIGN KEY("sessionId")
    REFERENCES "agent_session"("id")
    ON DELETE NO ACTION
    ON UPDATE NO ACTION;


--
-- MIGRATION VERSION FOR mineos_remote
--
INSERT INTO "serverpod_migrations" ("module", "version", "timestamp")
    VALUES ('mineos_remote', '20261121230344355', now())
    ON CONFLICT ("module")
    DO UPDATE SET "version" = '20261121230344355', "timestamp" = now();

--
-- MIGRATION VERSION FOR serverpod
--
INSERT INTO "serverpod_migrations" ("module", "version", "timestamp")
    VALUES ('serverpod', '20260824182259319', now())
    ON CONFLICT ("module")
    DO UPDATE SET "version" = '20260824182259319', "timestamp" = now();

--
-- MIGRATION VERSION FOR serverpod_auth_idp
--
INSERT INTO "serverpod_migrations" ("module", "version", "timestamp")
    VALUES ('serverpod_auth_idp', '20261015164015382', now())
    ON CONFLICT ("module")
    DO UPDATE SET "version" = '20261015164015382', "timestamp" = now();

--
-- MIGRATION VERSION FOR serverpod_auth_core
--
INSERT INTO "serverpod_migrations" ("module", "version", "timestamp")
    VALUES ('serverpod_auth_core', '20260924105232991', now())
    ON CONFLICT ("module")
    DO UPDATE SET "version" = '20260924105232991', "timestamp" = now();


COMMIT;
