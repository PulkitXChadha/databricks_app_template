# Frontend Component Instrumentation Checklist

**Feature**: 006-app-metrics  
**Purpose**: Track completion of usage tracking instrumentation across all user-facing components  
**Created**: 2025-10-21  
**Task Reference**: T079.5

## Overview

This checklist tracks the instrumentation of usage tracking for FR-010 comprehensive user interaction tracking. All interactive components should track relevant user actions to provide complete product analytics.

---

## Required Instrumentation

### Core Application Pages ✓

- [X] **DatabricksServicesPage** - Page view tracking on tab changes
  - Location: `client/src/pages/DatabricksServicesPage.tsx`
  - Events: `page_view` on activeTab change
  - Status: COMPLETE (T079)

### Form Components ✓

- [X] **PreferencesForm** - Preference save/delete tracking
  - Location: `client/src/components/ui/PreferencesForm.tsx`
  - Events: `form_submit` with success/failure status
  - Status: COMPLETE (T081)

- [X] **ModelInvokeForm** - Model invocation tracking
  - Location: `client/src/components/ui/ModelInvokeForm.tsx`
  - Events: `model_invoked` with endpoint and execution time
  - Status: COMPLETE (T081)

### Query Components ✓

- [X] **DataTable** - Query execution tracking
  - Location: `client/src/components/ui/DataTable.tsx`
  - Events: `query_executed`, `button_click` (pagination), `preference_changed` (page size)
  - Status: COMPLETE (T079.5)

### Dashboard Components ✓

- [X] **MetricsDashboard** - Dashboard interaction tracking
  - Location: `client/src/components/MetricsDashboard.tsx`
  - Events: `button_click` (refresh button), `preference_changed` (time range selector)
  - Status: COMPLETE (T079.5)

### Navigation Components ✓

- [X] **Sidebar** - Navigation menu clicks
  - Location: `client/src/pages/DatabricksServicesPage.tsx`
  - Events: `button_click` for all navigation menu items (Welcome, Unity Catalog, Model Serving, Preferences, Metrics)
  - Status: COMPLETE (T079.5)

---

## Instrumentation Coverage Audit

**Last Run**: 2025-10-21  
**Total Interactive Components**: 6  
**Fully Instrumented**: 6 (100%)  
**Partially Instrumented**: 0 (0%)  
**Not Instrumented**: 0 (0%)

### Audit Command

Run this command to identify un-instrumented interactive elements:

```bash
grep -r 'onClick\|onSubmit\|onChange' client/src/components/ client/src/pages/ --include='*.tsx' | \
  grep -v 'usageTracker' | \
  wc -l
```

**Expected Output**: Count of interactive elements without tracking

---

## Instrumentation Patterns

### Button Click Tracking

```typescript
import { usageTracker, getElementIdentifier } from '@/services/usageTracker';

const handleButtonClick = (e: React.MouseEvent<HTMLButtonElement>) => {
  const elementId = getElementIdentifier(e.currentTarget);
  
  usageTracker.track({
    event_type: 'button_click',
    page_name: location.pathname,
    element_id: elementId,
    metadata: {
      button_text: e.currentTarget.textContent
    }
  });
  
  // ... rest of button logic
};
```

### Form Submission Tracking

```typescript
import { usageTracker } from '@/services/usageTracker';

const handleFormSubmit = async (formData: any) => {
  try {
    await submitForm(formData);
    
    // Track successful submission
    usageTracker.track({
      event_type: 'form_submit',
      page_name: '/form-page',
      element_id: 'form-name',
      success: true,
      metadata: {
        field_count: Object.keys(formData).length
      }
    });
  } catch (error) {
    // Track failed submission
    usageTracker.track({
      event_type: 'form_submit',
      page_name: '/form-page',
      element_id: 'form-name',
      success: false,
      metadata: {
        error: error.message
      }
    });
  }
};
```

### High-Frequency Event Debouncing

```typescript
import { usageTracker, debounce } from '@/services/usageTracker';

// Debounce typing events (500ms delay per spec.md)
const handleSearchInput = debounce((searchTerm: string) => {
  usageTracker.track({
    event_type: 'search',
    page_name: '/search',
    element_id: 'search-input',
    metadata: {
      search_term: searchTerm,
      term_length: searchTerm.length
    }
  });
}, 500);
```

---

## Element Identifier Strategy

Per FR-010, use hybrid identifier strategy (T080):

1. **data-track-id** attribute (explicit, recommended)
   ```html
   <button data-track-id="submit-query-btn" onClick={...}>
   ```

2. **id** attribute (fallback)
   ```html
   <button id="submit-btn" onClick={...}>
   ```

3. **tagName.textContent** (automatic fallback)
   - Used when no explicit ID present
   - Example: "button.Submit Query"
   - Truncated to 100 characters per FR-010

---

## Remaining Work

### High Priority (Core Features)

1. **DataTable query execution** - Tracks most common user action (SQL queries)
2. **Sidebar navigation clicks** - Tracks feature discovery and usage patterns

### Medium Priority (Admin Features)

1. **MetricsDashboard interactions** - Refresh button, time range changes

### Low Priority (Nice-to-Have)

1. **Export buttons** - File download triggers
2. **Upload components** - File upload events

---

## Validation

After completing instrumentation, validate coverage with:

1. **Manual Testing**: Navigate through app, check browser console for usage tracker debug logs
2. **Network Inspection**: Verify batch submissions every 10 seconds or 20 events
3. **Backend Query**: Check `usage_events` table for recorded events
4. **Dashboard Verification**: View usage metrics in admin dashboard

---

## Success Criteria

- [X] All form submissions tracked (PreferencesForm, ModelInvokeForm)
- [X] Page view tracking on navigation
- [X] Query execution tracking (DataTable)
- [X] Navigation menu click tracking
- [X] Dashboard interaction tracking
- [X] >95% coverage of user-facing interactive elements

**Overall Progress**: 100% complete (6/6 components fully instrumented)

**Completed**:
1. ✅ Instrumented DataTable query execution, pagination, and page size controls
2. ✅ Added Sidebar navigation tracking for all menu items
3. ✅ Instrumented MetricsDashboard refresh button and time range selector
4. ✅ Achieved 100% coverage of identified interactive components

---

**Last Updated**: 2025-10-21  
**Owner**: Development Team

