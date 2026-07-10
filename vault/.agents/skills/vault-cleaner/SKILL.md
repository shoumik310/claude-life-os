---
name: vault-cleaner
description: Cleans up recently created files in the Obsidian vault, ensuring they follow naming conventions, use wikilinks, have correct frontmatter, are placed in the correct folders, and consolidates any orphans or duplicates.
---

# Vault Cleaner Skill

Use this skill when the user asks to "clean up," "consolidate," or "organize" files they created in the vault.

## Objective
Scan the vault for recently created, modified, or misplaced files, and format them to comply with the Mobius Obsidian vault rules.

## Step-by-Step Execution Plan

1. **Find Target Files**:
   * Inspect recent git changes or list files in the vault to identify new or modified `.md` files.
   * Check for files sitting in the root of the vault that should be placed in subfolders.

2. **Verify Placement**:
   * Read the frontmatter `type` property of each file.
   * Move the file to the subfolder matching its `type`:
     * `person` -> `People/`
     * `project` -> `Projects/`
     * `decision` -> `Decisions/`
     * `catchup` -> `Catchups/` (calls, dinners, hangouts, visits — personal equivalent of meeting notes)
     * `daily` -> `Daily/`
     * `knowledge` -> `Knowledge/` (general reference material only, not a catch-all)
   * Non-note attachments (PDFs, screenshots, exports) belong in `Attachments/`, not loose at vault root.

3. **Format Naming & Titles**:
   * Ensure filenames match the title format (e.g., `Jane Doe.md`, not `jane_doe_notes.md` or `jane_doe`).
   * Filenames are case-sensitive titles and should be formatted exactly as they should read in links.

4. **Audit and Standardize Note Conventions**:
   * **Frontmatter**: Ensure every note begins with standard YAML frontmatter properties:
     ```yaml
     ---
     type: <type>
     created: YYYY-MM-DD
     tags: []
     aliases: []
     ---
     ```
   * **Wikilinks**: Scan note bodies and convert any relative markdown links `[Text](path.md)` to wikilinks `[[Note Name]]`.
   * **No Proactive MOCs**: Do not build a Map of Content (MOC) unless a folder is already crowded and messy.

5. **Consolidate and Deduplicate**:
   * Run the nightly consolidation logic:
     1. Identify orphan links/notes (mentions of people, projects, companies, etc. that do not have their own files yet) and ask the user if they want to create stub files for them.
     2. Identify and consolidate duplicate notes.
     3. Update existing MOCs with new links.
     4. Flag strategic items for the user to review.
