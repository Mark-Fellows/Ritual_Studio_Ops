-- Private storage bucket for teacher application CVs (pdf/doc/docx, max 1 MB).
-- Applied via Supabase MCP 2026-06-01. Additive.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
SELECT 'teacher-cvs','teacher-cvs', false, 1048576,
       ARRAY['application/pdf','application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document']
WHERE NOT EXISTS (SELECT 1 FROM storage.buckets WHERE id='teacher-cvs');

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND policyname='teacher_cvs_auth_read') THEN
    CREATE POLICY "teacher_cvs_auth_read" ON storage.objects
      FOR SELECT TO authenticated USING (bucket_id = 'teacher-cvs');
  END IF;
END $$;
