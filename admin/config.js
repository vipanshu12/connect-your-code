// Supabase project connection.
//
// Both values are safe to publish: the anon key is designed to ship in
// client-side code, and every table is protected by the row level security
// policies in supabase/policies.sql - reads are public, writes require a
// signed-in user. The service_role key must NEVER appear here.
export const SUPABASE_URL = "https://oduodcumgregnkmdcmju.supabase.co";
export const SUPABASE_ANON_KEY = "sb_publishable_8WoG0_-72OfaIEQRdBOXXw_QFLCKxC5";

// Storage bucket created by supabase/policies.sql.
export const MEDIA_BUCKET = "media";

// Vercel Deploy Hook - the Publish button POSTs here to rebuild the live site.
// Create it at: Vercel project -> Settings -> Git -> Deploy Hooks.
// Anyone who has this URL can trigger a rebuild (nothing more), so treat it as
// low-risk but not secret. Leave blank to hide the Publish button.
export const DEPLOY_HOOK = "";
