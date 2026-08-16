// Generated from app/views.py - do not edit by hand.
// Regenerate: python3 tools/gen_admin_schema.py
//
// Mirrors SECTIONS, SETTING_GROUPS, SEO_GROUPS and PAGE_SEO_FIELDS so the
// JavaScript admin edits exactly the fields the Python admin edited.
export const SCHEMA = {
  "sections": {
    "services": {
      "table": "services",
      "label": "Services",
      "icon": "ri-hammer-line",
      "order": "sort, id",
      "fields": [
        {
          "name": "title",
          "kind": "text",
          "label": "Title"
        },
        {
          "name": "description",
          "kind": "textarea",
          "label": "Description"
        },
        {
          "name": "icon",
          "kind": "text",
          "label": "Icon"
        },
        {
          "name": "image",
          "kind": "image",
          "label": "Image"
        },
        {
          "name": "features",
          "kind": "textarea",
          "label": "Features"
        },
        {
          "name": "sort",
          "kind": "number",
          "label": "Sort"
        },
        {
          "name": "active",
          "kind": "bool",
          "label": "Active"
        },
        {
          "name": "featured",
          "kind": "bool",
          "label": "Featured"
        }
      ]
    },
    "projects": {
      "table": "projects",
      "label": "Projects",
      "icon": "ri-building-2-line",
      "order": "sort, id",
      "fields": [
        {
          "name": "title",
          "kind": "text",
          "label": "Title"
        },
        {
          "name": "location",
          "kind": "text",
          "label": "Location"
        },
        {
          "name": "category",
          "kind": "text",
          "label": "Category"
        },
        {
          "name": "status",
          "kind": "text",
          "label": "Status"
        },
        {
          "name": "completion",
          "kind": "text",
          "label": "Completion"
        },
        {
          "name": "description",
          "kind": "textarea",
          "label": "Description"
        },
        {
          "name": "image",
          "kind": "image",
          "label": "Image"
        },
        {
          "name": "sort",
          "kind": "number",
          "label": "Sort"
        },
        {
          "name": "active",
          "kind": "bool",
          "label": "Active"
        },
        {
          "name": "featured",
          "kind": "bool",
          "label": "Featured"
        }
      ]
    },
    "team": {
      "table": "team",
      "label": "Team",
      "icon": "ri-team-line",
      "order": "sort, id",
      "fields": [
        {
          "name": "name",
          "kind": "text",
          "label": "Name"
        },
        {
          "name": "role",
          "kind": "text",
          "label": "Role"
        },
        {
          "name": "bio",
          "kind": "textarea",
          "label": "Bio"
        },
        {
          "name": "image",
          "kind": "image",
          "label": "Image"
        },
        {
          "name": "linkedin",
          "kind": "text",
          "label": "Linkedin"
        },
        {
          "name": "email",
          "kind": "text",
          "label": "Email"
        },
        {
          "name": "sort",
          "kind": "number",
          "label": "Sort"
        },
        {
          "name": "active",
          "kind": "bool",
          "label": "Active"
        }
      ]
    },
    "testimonials": {
      "table": "testimonials",
      "label": "Testimonials",
      "icon": "ri-chat-quote-line",
      "order": "sort, id",
      "fields": [
        {
          "name": "name",
          "kind": "text",
          "label": "Name"
        },
        {
          "name": "company",
          "kind": "text",
          "label": "Company"
        },
        {
          "name": "quote",
          "kind": "textarea",
          "label": "Quote"
        },
        {
          "name": "rating",
          "kind": "number",
          "label": "Rating"
        },
        {
          "name": "image",
          "kind": "image",
          "label": "Image"
        },
        {
          "name": "sort",
          "kind": "number",
          "label": "Sort"
        },
        {
          "name": "active",
          "kind": "bool",
          "label": "Active"
        }
      ]
    },
    "jobs": {
      "table": "jobs",
      "label": "Careers",
      "icon": "ri-briefcase-line",
      "order": "sort, id",
      "fields": [
        {
          "name": "title",
          "kind": "text",
          "label": "Title"
        },
        {
          "name": "location",
          "kind": "text",
          "label": "Location"
        },
        {
          "name": "experience",
          "kind": "text",
          "label": "Experience"
        },
        {
          "name": "employment",
          "kind": "text",
          "label": "Employment"
        },
        {
          "name": "description",
          "kind": "textarea",
          "label": "Description"
        },
        {
          "name": "sort",
          "kind": "number",
          "label": "Sort"
        },
        {
          "name": "active",
          "kind": "bool",
          "label": "Active"
        }
      ]
    },
    "faqs": {
      "table": "faqs",
      "label": "FAQs",
      "icon": "ri-question-line",
      "order": "sort, id",
      "fields": [
        {
          "name": "question",
          "kind": "text",
          "label": "Question"
        },
        {
          "name": "answer",
          "kind": "textarea",
          "label": "Answer"
        },
        {
          "name": "page",
          "kind": "text",
          "label": "Page"
        },
        {
          "name": "sort",
          "kind": "number",
          "label": "Sort"
        },
        {
          "name": "active",
          "kind": "bool",
          "label": "Active"
        }
      ]
    }
  },
  "settingGroups": [
    {
      "title": "Hero Section",
      "fields": [
        {
          "name": "hero_heading",
          "label": "Headline (HTML allowed)",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "hero_text",
          "label": "Sub-heading",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "hero_image",
          "label": "Background image",
          "kind": "image",
          "help": ""
        }
      ]
    },
    {
      "title": "About Section",
      "fields": [
        {
          "name": "about_heading",
          "label": "Heading",
          "kind": "text",
          "help": ""
        },
        {
          "name": "about_text",
          "label": "Body copy",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "about_image",
          "label": "Image",
          "kind": "image",
          "help": ""
        }
      ]
    },
    {
      "title": "Mission, Vision & Values",
      "fields": [
        {
          "name": "mission",
          "label": "Mission",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "vision",
          "label": "Vision",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "values",
          "label": "Values",
          "kind": "textarea",
          "help": ""
        }
      ]
    },
    {
      "title": "Statistics",
      "fields": [
        {
          "name": "stat_years",
          "label": "Years of experience",
          "kind": "text",
          "help": ""
        },
        {
          "name": "stat_projects",
          "label": "Projects completed",
          "kind": "text",
          "help": ""
        },
        {
          "name": "stat_clients",
          "label": "Satisfied clients",
          "kind": "text",
          "help": ""
        },
        {
          "name": "stat_workforce",
          "label": "Workforce size",
          "kind": "text",
          "help": ""
        }
      ]
    },
    {
      "title": "Contact Details",
      "fields": [
        {
          "name": "phone",
          "label": "Primary phone",
          "kind": "text",
          "help": ""
        },
        {
          "name": "phone_alt",
          "label": "Secondary phone",
          "kind": "text",
          "help": ""
        },
        {
          "name": "email",
          "label": "General email",
          "kind": "text",
          "help": ""
        },
        {
          "name": "email_careers",
          "label": "Careers email",
          "kind": "text",
          "help": ""
        },
        {
          "name": "address",
          "label": "Office address",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "hours",
          "label": "Working hours",
          "kind": "text",
          "help": ""
        },
        {
          "name": "map_embed",
          "label": "Google Maps embed URL",
          "kind": "textarea",
          "help": ""
        }
      ]
    },
    {
      "title": "Social Links",
      "fields": [
        {
          "name": "facebook",
          "label": "Facebook URL",
          "kind": "text",
          "help": ""
        },
        {
          "name": "instagram",
          "label": "Instagram URL",
          "kind": "text",
          "help": ""
        },
        {
          "name": "linkedin",
          "label": "LinkedIn URL",
          "kind": "text",
          "help": ""
        },
        {
          "name": "whatsapp",
          "label": "WhatsApp URL",
          "kind": "text",
          "help": ""
        }
      ]
    },
    {
      "title": "Footer & SEO",
      "fields": [
        {
          "name": "site_name",
          "label": "Company name",
          "kind": "text",
          "help": ""
        },
        {
          "name": "footer_text",
          "label": "Footer description",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "seo_title",
          "label": "Default page title",
          "kind": "text",
          "help": ""
        },
        {
          "name": "seo_description",
          "label": "Meta description",
          "kind": "textarea",
          "help": ""
        }
      ]
    }
  ],
  "seoGroups": [
    {
      "title": "Global SEO",
      "fields": [
        {
          "name": "seo_site_url",
          "label": "Website address (https://...)",
          "kind": "text",
          "help": "Everything absolute is built from this: canonical tags, the sitemap, share images and all structured data. Google ignores relative URLs."
        },
        {
          "name": "seo_title",
          "label": "Default page title",
          "kind": "text",
          "help": "Used when a page has no title of its own."
        },
        {
          "name": "seo_title_suffix",
          "label": "Title suffix",
          "kind": "text",
          "help": "Appended to every page title, e.g. ' | Sharma Interior Construction'."
        },
        {
          "name": "seo_description",
          "label": "Default meta description",
          "kind": "textarea",
          "help": ""
        },
        {
          "name": "seo_default_image",
          "label": "Default share image",
          "kind": "image",
          "help": "Shown when a page is posted to WhatsApp, Facebook or LinkedIn. 1200x630 is ideal."
        },
        {
          "name": "seo_keywords",
          "label": "Keywords",
          "kind": "textarea",
          "help": "Google ignores this tag, but Bing still reads it and it keeps your target terms written down in one place."
        },
        {
          "name": "seo_noindex_site",
          "label": "Hide the whole site from Google (0 or 1)",
          "kind": "text",
          "help": "Set to 1 while the site is unfinished. Remember to set it back to 0 at launch."
        }
      ]
    },
    {
      "title": "Search Console & Analytics",
      "fields": [
        {
          "name": "seo_verification",
          "label": "Google Search Console verification code",
          "kind": "text",
          "help": "Paste only the content value from the meta tag Google gives you."
        },
        {
          "name": "seo_bing_verification",
          "label": "Bing Webmaster verification code",
          "kind": "text",
          "help": ""
        },
        {
          "name": "ga_measurement_id",
          "label": "Google Analytics 4 ID",
          "kind": "text",
          "help": "Looks like G-XXXXXXXXXX. Leave blank for no tracking."
        },
        {
          "name": "gtm_id",
          "label": "Google Tag Manager ID",
          "kind": "text",
          "help": "Looks like GTM-XXXXXXX."
        },
        {
          "name": "seo_twitter_handle",
          "label": "X / Twitter handle",
          "kind": "text",
          "help": "With the @."
        }
      ]
    },
    {
      "title": "Local SEO - business details",
      "fields": [
        {
          "name": "biz_legal_name",
          "label": "Registered business name",
          "kind": "text",
          "help": "Must match your Google Business Profile exactly."
        },
        {
          "name": "biz_street",
          "label": "Street address",
          "kind": "text",
          "help": ""
        },
        {
          "name": "biz_city",
          "label": "City",
          "kind": "text",
          "help": ""
        },
        {
          "name": "biz_state",
          "label": "State",
          "kind": "text",
          "help": ""
        },
        {
          "name": "biz_postal",
          "label": "PIN code",
          "kind": "text",
          "help": ""
        },
        {
          "name": "biz_country",
          "label": "Country code",
          "kind": "text",
          "help": "Two letters, e.g. IN."
        },
        {
          "name": "biz_lat",
          "label": "Latitude",
          "kind": "text",
          "help": ""
        },
        {
          "name": "biz_lng",
          "label": "Longitude",
          "kind": "text",
          "help": ""
        },
        {
          "name": "biz_hours_spec",
          "label": "Opening hours",
          "kind": "text",
          "help": "Exact format \"Mo-Sa 09:00-18:00\" - anything else is skipped in the schema."
        },
        {
          "name": "biz_areas",
          "label": "Service areas",
          "kind": "textarea",
          "help": "Comma separated. Only list places you actually work."
        },
        {
          "name": "biz_price_range",
          "label": "Price range",
          "kind": "text",
          "help": "$ to $$$$."
        },
        {
          "name": "biz_founded",
          "label": "Year founded",
          "kind": "text",
          "help": ""
        },
        {
          "name": "biz_profile_url",
          "label": "Google Business Profile URL",
          "kind": "text",
          "help": ""
        }
      ]
    }
  ],
  "pageSeoFields": [
    "title",
    "description",
    "keyword",
    "og_title",
    "og_desc",
    "og_image",
    "canonical",
    "changefreq",
    "priority"
  ],
  "routes": [
    "/",
    "/about.html",
    "/contact.html",
    "/index.html",
    "/project.html",
    "/service.html"
  ]
};
