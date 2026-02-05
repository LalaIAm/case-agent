# Accessibility

## Overview

The Minnesota Conciliation Court Case Agent aims to be usable with keyboard and screen readers and to follow WCAG-oriented practices.

## Features

- **ARIA**: Interactive elements use `aria-label`, `aria-describedby`, or visible labels. Error messages are associated with inputs via `aria-describedby` and `role="alert"` where appropriate.
- **Focus**: Buttons and links use visible focus styles (e.g. `focus:ring-2`). Modals and dialogs should trap focus and restore it on close (when implemented).
- **Headings**: Pages use a logical heading hierarchy (`h1` for page title, then `h2`/`h3` for sections).
- **Forms**: Required fields use `required` and `aria-describedby` for validation errors. Labels are associated with inputs via `htmlFor`/`id`.
- **Live regions**: Toasts use `aria-live="polite"`; error boundaries use `aria-live="assertive"` for critical errors.
- **Status**: Loading and progress use `role="status"` or `role="progressbar"` with `aria-valuenow` / `aria-valuemin` / `aria-valuemax` where applicable.

## Keyboard navigation

- **Tab**: Move between focusable elements.
- **Enter**: Activate buttons and links.
- **Escape**: Close modals/dialogs (when implemented).
- **Arrow keys**: Used in list/menu components that integrate `useKeyboardNavigation` (e.g. step lists).

The `useKeyboardNavigation` hook supports:

- Arrow Up/Down (or Left/Right for horizontal lists).
- Home/End to jump to first/last item.
- Optional wrap at list ends.

## Screen readers

- Notifications (toasts) are announced via `aria-live`.
- Errors are exposed with `role="alert"` and linked to fields with `aria-describedby`.
- Progress and connection status use `role="status"` or `role="progressbar"`.

## WCAG compliance

The app is developed with WCAG 2.1 Level AA in mind (contrast, focus visibility, labels, errors). A full audit would be needed to claim formal compliance.

## File upload

The file upload component supports:

- Keyboard activation (focus and Enter/Space).
- Clear label and, where applicable, an `aria-live` region for upload progress so screen readers get updates.
