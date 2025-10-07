# UI Component Migration Mapping: shadcn/ui → DesignBricks

**Task**: T051 - Audit DesignBricks component availability  
**Date**: October 7, 2025  
**DesignBricks Version**: v0.2.2  
**Fallback Package**: @databricks/design-system v1.12.22  
**Documentation**: https://pulkitxchadha.github.io/DesignBricks/

## Executive Summary

This document maps all current shadcn/ui components to their DesignBricks equivalents, identifies gaps requiring @databricks/design-system fallback, and provides a migration strategy for Phase 3.15 (T051-T058).

**Status**: ✅ Audit Complete  
**Outcome**: All shadcn/ui components have viable DesignBricks or @databricks/design-system equivalents  
**Deprecated Components**: None identified (✅ Safe to proceed)

---

## Component Mapping Table

| shadcn/ui Component | Current Usage | DesignBricks Equivalent | Fallback Strategy | Migration Priority |
|---------------------|---------------|-------------------------|-------------------|-------------------|
| **Card** | WelcomePage (9 instances)<br>DatabricksServicesPage (4 instances) | ✅ `Card` (Data Display) | N/A | **HIGH** (T053) |
| **CardContent** | Both pages | ✅ Part of `Card` component | N/A | **HIGH** (T053) |
| **CardHeader** | Both pages | ✅ Part of `Card` component | N/A | **HIGH** (T053) |
| **CardTitle** | Both pages | ✅ Part of `Card` component | N/A | **HIGH** (T053) |
| **CardDescription** | Both pages | ✅ Part of `Card` component | N/A | **HIGH** (T053) |
| **Button** | WelcomePage (1 instance)<br>DatabricksServicesPage (1 instance)<br>PreferencesForm<br>ModelInvokeForm | ✅ `Button` (Foundation) | N/A | **HIGH** (T054) |
| **Badge** | WelcomePage (13 instances) | ✅ `Badge` (Feedback) | N/A | **MEDIUM** (T056) |
| **Input** | DatabricksServicesPage (3 instances)<br>PreferencesForm<br>ModelInvokeForm | ✅ `TextField` (Inputs) | N/A | **HIGH** (T055) |
| **Alert** | DatabricksServicesPage (error display) | ✅ `Alert` (Feedback) | N/A | **MEDIUM** (T056) |
| **AlertDescription** | DatabricksServicesPage | ✅ Part of `Alert` component | N/A | **MEDIUM** (T056) |
| **Tabs** | Not currently used (legacy) | ✅ `Tabs` (Navigation) | N/A | **LOW** (cleanup) |
| **Skeleton** | Not currently used | ❌ Not available | ⚠️ @databricks/design-system `Skeleton` | **LOW** (if needed) |
| **DataTable** | Custom component in DatabricksServicesPage | ✅ `Table` (Data Display) | N/A | **CRITICAL** (T057) |

---

## Available DesignBricks Components

### ✅ Feedback Components
- **Alert**: User notifications, error messages, warnings
- **Badge**: Status indicators, labels, tags
- **Progress**: Loading indicators, progress bars

### ✅ Data Display Components
- **Card**: Content containers with header/body/footer (✅ Direct replacement)
- **Table**: Data tables with sorting, pagination (✅ Direct replacement)
- **List**: Ordered/unordered lists
- **AreaChart, BarChart, LineChart, MultiLineChart, PieChart, ScatterChart**: Data visualization

### ✅ Navigation Components
- **Breadcrumbs**: Navigation hierarchy
- **Sidebar**: Side navigation panel (✅ Already implemented)
- **Tabs**: Tabbed content switcher
- **TopBar**: Top navigation bar (✅ Already implemented)

### ✅ Foundation Components
- **Button**: Primary UI actions (✅ Direct replacement)
- **Colors**: Design system color palette
- **Typography**: Text styling system
- **UserAvatar**: User profile images

### ✅ Input Components
- **Checkbox**: Boolean input
- **PillControl**: Multi-select pills
- **SearchInput**: Search text input
- **Select**: Dropdown selection
- **TextField**: Text input field (✅ Direct replacement for Input)

### ✅ Overlay Components
- **Dropdown**: Dropdown menus
- **Tooltip**: Hover tooltips

### ✅ Layout Components
- **Flex**: Flexbox layout
- **Grid**: Grid layout
- **GridItem**: Grid item wrapper

---

## Migration Strategy by Task

### T053: Replace Card Components
**Files**: WelcomePage.tsx (9 instances), DatabricksServicesPage.tsx (4 instances)  
**DesignBricks Component**: `Card` (Data Display category)  
**Migration Path**: 
1. Import `Card` from `designbricks` instead of `@/components/ui/card`
2. Replace `CardContent`, `CardHeader`, `CardTitle`, `CardDescription` with DesignBricks `Card` props/children
3. Verify visual layout matches current design
4. Test all card interactions (expand/collapse if applicable)
5. Remove `/client/src/components/ui/card.tsx` after migration

**Risk**: ❌ None - Direct 1:1 mapping available

### T054: Replace Button Components
**Files**: WelcomePage.tsx, DatabricksServicesPage.tsx, PreferencesForm.tsx, ModelInvokeForm.tsx  
**DesignBricks Component**: `Button` (Foundation category)  
**Migration Path**:
1. Import `Button` from `designbricks` instead of `@/components/ui/button`
2. Map shadcn/ui button variants to DesignBricks equivalents:
   - `default` → `primary`
   - `outline` → `secondary` or `outlined`
   - `destructive` → `danger`
   - `ghost` → `text`
3. Verify onClick handlers, disabled states, loading states
4. Test keyboard navigation (Enter, Space)
5. Remove `/client/src/components/ui/button.tsx` after migration

**Risk**: ⚠️ **LOW** - Variant names may differ, test all button states

### T055: Replace Input Components
**Files**: DatabricksServicesPage.tsx (3 catalog/schema/table inputs), PreferencesForm.tsx, ModelInvokeForm.tsx  
**DesignBricks Component**: `TextField` (Inputs category)  
**Migration Path**:
1. Import `TextField` from `designbricks` instead of `Input` from `@/components/ui/input`
2. Map shadcn/ui Input props to DesignBricks TextField:
   - `value` → `value`
   - `onChange` → `onChange`
   - `placeholder` → `placeholder`
   - `disabled` → `disabled`
3. Verify form validation (error states, required fields)
4. Test JSON input fields in ModelInvokeForm (may need `multiline` or `textarea` variant)
5. Remove `/client/src/components/ui/input.tsx` after migration

**Risk**: ⚠️ **MEDIUM** - JSON editor in ModelInvokeForm may need special handling (multiline TextField or custom textarea)

### T056: Replace Alert/Badge Components
**Files**: WelcomePage.tsx (Badge: 13 instances), DatabricksServicesPage.tsx (Alert: error display)  
**DesignBricks Components**: `Alert` (Feedback), `Badge` (Feedback)  
**Migration Path**:

**Badge Migration**:
1. Import `Badge` from `designbricks` instead of `@/components/ui/badge`
2. Map shadcn/ui Badge variants to DesignBricks:
   - `default` → `default` or `primary`
   - `secondary` → `secondary`
   - `outline` → `outlined`
3. Verify badge styling in tech stack section (WelcomePage lines 279-331)
4. Remove `/client/src/components/ui/badge.tsx` after migration

**Alert Migration**:
1. Import `Alert` from `designbricks` instead of `@/components/ui/alert`
2. Map shadcn/ui Alert variants to DesignBricks:
   - `destructive` → `error` or `danger`
   - `default` → `info`
3. Replace `AlertDescription` with DesignBricks Alert children/content
4. Test error display in Unity Catalog query section (DatabricksServicesPage line 334)
5. Remove `/client/src/components/ui/alert.tsx` after migration

**Risk**: ❌ None - Direct 1:1 mapping available

### T057: Migrate DataTable Component
**Files**: `/client/src/components/ui/DataTable.tsx`, DatabricksServicesPage.tsx (usage)  
**DesignBricks Component**: `Table` (Data Display category)  
**Migration Path**:
1. Read current DataTable.tsx implementation to understand:
   - Column rendering logic
   - Row data mapping
   - Pagination controls (prev/next, page size selector)
   - Loading skeleton states
   - Error handling display
2. Rewrite using DesignBricks `Table` component:
   - Map columns from Unity Catalog schema to DesignBricks Table columns
   - Implement pagination using DesignBricks Table pagination props/events
   - Add loading state with DesignBricks Progress or Skeleton (if available)
   - Add error state with DesignBricks Alert
3. Test with Unity Catalog query results:
   - Query main.samples.demo_data
   - Verify column headers render correctly
   - Click "Next Page" button, verify API call with offset+limit
   - Change page size (10/25/50/100), verify API call
   - Test loading state (show skeleton during fetch)
   - Test error state (disconnect from UC, verify error message)
4. Test keyboard navigation:
   - Tab through table cells
   - Verify focus indicators visible
5. Update DatabricksServicesPage.tsx to use new DataTable
6. Keep DataTable.tsx file (custom wrapper around DesignBricks Table)

**Risk**: ⚠️ **HIGH** - Most complex migration, DataTable has custom pagination logic
- DesignBricks Table may have different pagination API
- Loading/error states may need custom implementation
- Unity Catalog column schema must map correctly to Table columns

**Acceptance Criteria**:
1. Query Unity Catalog table → Results display in DesignBricks Table
2. Pagination works (next/prev buttons, page size selector)
3. Loading state shows during API calls
4. Error state shows when query fails
5. Column headers render from DataSource.columns
6. Keyboard navigation works (Tab through cells)
7. No visual regressions compared to current DataTable

---

## Fallback Components (@databricks/design-system)

### Skeleton (Loading State)
**Status**: ❌ Not available in DesignBricks v0.2.2  
**Fallback**: @databricks/design-system `Skeleton` component  
**Usage**: Loading states in DataTable, card content, list items  
**Verification**: Check @databricks/design-system docs to ensure `Skeleton` is not deprecated  
**Action**: If DesignBricks adds Progress component, migrate from Skeleton to Progress

**Alternative**: Use DesignBricks `Progress` component (available in Feedback category) instead of Skeleton

---

## Deprecated Component Check

**Result**: ✅ **NO DEPRECATED COMPONENTS IDENTIFIED**

**Methodology**:
1. Reviewed @databricks/design-system v1.12.22 changelog and documentation
2. Checked npm package deprecation warnings (`bun add` output)
3. Verified all proposed fallback components are actively maintained
4. Confirmed DesignBricks v0.2.2 is latest stable version

**Conclusion**: Safe to proceed with migration using both DesignBricks and @databricks/design-system

---

## Files to Remove After Migration

After completing T053-T057, the following shadcn/ui component files should be deleted:

1. ✅ `/client/src/components/ui/card.tsx` (after T053)
2. ✅ `/client/src/components/ui/button.tsx` (after T054)
3. ✅ `/client/src/components/ui/input.tsx` (after T055)
4. ✅ `/client/src/components/ui/badge.tsx` (after T056)
5. ✅ `/client/src/components/ui/alert.tsx` (after T056)
6. ⚠️ `/client/src/components/ui/tabs.tsx` (unused, safe to delete)
7. ⚠️ `/client/src/components/ui/skeleton.tsx` (replace with DesignBricks Progress or @databricks/design-system Skeleton)

**Keep** (custom components wrapping DesignBricks):
- `/client/src/components/ui/DataTable.tsx` (custom wrapper around DesignBricks Table)
- `/client/src/components/ui/PreferencesForm.tsx` (custom form using DesignBricks components)
- `/client/src/components/ui/ModelInvokeForm.tsx` (custom form using DesignBricks components)

---

## Migration Checklist

### Pre-Migration Validation
- [x] DesignBricks v0.2.2 documentation reviewed
- [x] @databricks/design-system v1.12.22 installed
- [x] All shadcn/ui components identified (10 total)
- [x] Component mapping table complete (100% coverage)
- [x] Deprecated component check complete (✅ None found)
- [x] Migration tasks T053-T058 defined in tasks.md

### Migration Order
1. **T053**: Card components (13 instances across 2 files) - **HIGH PRIORITY**
2. **T054**: Button components (4 files) - **HIGH PRIORITY**
3. **T055**: Input/TextField components (3 files) - **HIGH PRIORITY**
4. **T056**: Alert/Badge components (2 files) - **MEDIUM PRIORITY**
5. **T057**: DataTable component (1 complex file) - **CRITICAL** (depends on T053, T054)
6. **T058**: Visual consistency & accessibility validation - **GATE** (depends on all above)

### Post-Migration Validation (T058)
- [ ] No imports from `@/components/ui/card`
- [ ] No imports from `@/components/ui/button`
- [ ] No imports from `@/components/ui/input`
- [ ] No imports from `@/components/ui/badge`
- [ ] No imports from `@/components/ui/alert`
- [ ] All component interactions functional (onClick, onChange, form validation)
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Visual consistency with Databricks design standards
- [ ] Lighthouse accessibility score ≥90 (WCAG 2.1 Level A)
- [ ] No TypeScript errors
- [ ] No console warnings in browser DevTools

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| DesignBricks Card API differs from shadcn/ui | **LOW** | **MEDIUM** | Read DesignBricks Card docs, test all card layouts |
| Button variant names mismatch | **LOW** | **HIGH** | Document variant mapping, test all button states |
| TextField doesn't support multiline (JSON editor) | **MEDIUM** | **MEDIUM** | Use @databricks/design-system TextArea or DesignBricks TextField with multiline prop |
| DataTable pagination API incompatibility | **HIGH** | **MEDIUM** | Read DesignBricks Table docs, implement custom pagination wrapper if needed |
| Visual regressions during migration | **MEDIUM** | **HIGH** | Take before/after screenshots, test on multiple screen sizes |
| Accessibility regressions | **HIGH** | **LOW** | Run Lighthouse audit before and after migration, test keyboard navigation |

---

## Success Criteria

### Phase 3.15 Complete When:
1. ✅ All shadcn/ui component imports removed from codebase
2. ✅ All UI components sourced from DesignBricks or @databricks/design-system
3. ✅ No deprecated components from @databricks/design-system in use
4. ✅ Visual consistency maintained (before/after screenshots match)
5. ✅ Lighthouse accessibility score ≥90 (WCAG 2.1 Level A compliance)
6. ✅ All CRUD operations functional (Unity Catalog, Preferences, Model Serving)
7. ✅ Keyboard navigation works for all interactive elements
8. ✅ No TypeScript errors or console warnings
9. ✅ DataTable pagination works correctly with Unity Catalog queries
10. ✅ All component interactions (forms, buttons, alerts) functional

---

## Appendix: DesignBricks Component Categories

**Implemented in DesignBricks v0.2.2**:
- Feedback: Alert, Badge, Progress
- Data Display: AreaChart, BarChart, Card, LineChart, List, MultiLineChart, PieChart, ScatterChart, Table
- Navigation: Breadcrumbs, Sidebar, Tabs, TopBar
- Foundation: Button, Colors, Typography, UserAvatar
- Inputs: Checkbox, PillControl, SearchInput, Select, TextField
- Overlays: Dropdown, Tooltip
- Layout: Flex, Grid, GridItem

**Missing from DesignBricks** (use @databricks/design-system):
- Skeleton (loading state) - **Alternative**: Use DesignBricks `Progress` component

---

**Document Status**: ✅ Complete - Ready for T053-T058 execution  
**Next Steps**: Begin T053 (Card component migration) and T054 (Button component migration) in parallel  
**Estimated Total Migration Time**: 12-18 hours across 8 tasks

