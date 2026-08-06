# 🎨 UI Components Library

This document describes the reusable UI components created during the design refinement process.

---

## Button Component

**Location:** `components/ui/button.tsx`

### Usage

```tsx
import Button from "@/components/ui/button";
import { Heart } from "lucide-react";

// Basic button
<Button>Click me</Button>

// Different variants
<Button variant="primary">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="danger">Danger</Button>

// Different sizes
<Button size="sm">Small</Button>
<Button size="md">Medium</Button>
<Button size="lg">Large</Button>

// With icon
<Button icon={<Heart />}>Like</Button>
<Button icon={<Heart />} iconPosition="right">Like This</Button>

// Loading state
<Button isLoading>Saving...</Button>

// Full width
<Button fullWidth>Full Width Button</Button>

// Disabled
<Button disabled>Disabled</Button>

// Custom className
<Button className="custom-class">Styled</Button>
```

### Props

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
  iconPosition?: "left" | "right";
  isLoading?: boolean;
  fullWidth?: boolean;
}
```

### Features
- 4 visual variants (primary, secondary, ghost, danger)
- 3 size options (sm, md, lg)
- Icon support with positioning
- Loading spinner
- Keyboard focus states with ring
- Disabled state support
- Smooth transitions (300ms)
- TypeScript support

---

## Card Component

**Location:** `components/ui/card.tsx`

### Usage

```tsx
import Card, { CardHeader, CardBody, CardFooter } from "@/components/ui/card";
import { Heart } from "lucide-react";

// Basic card
<Card>
  <p>Card content</p>
</Card>

// Different variants
<Card variant="elevated">Elevated (default)</Card>
<Card variant="outlined">Outlined</Card>
<Card variant="filled">Filled</Card>

// Interactive card
<Card interactive onClick={() => console.log("clicked")}>
  Click me
</Card>

// Card with structure
<Card>
  <CardHeader
    title="Card Title"
    subtitle="Optional subtitle"
    icon={<Heart />}
    action={<Button size="sm">Action</Button>}
  />
  <CardBody>
    <p>Main content goes here</p>
  </CardBody>
  <CardFooter>
    <Button fullWidth>Footer Button</Button>
  </CardFooter>
</Card>
```

### Props

```typescript
interface CardProps {
  children: ReactNode;
  variant?: "elevated" | "outlined" | "filled";
  interactive?: boolean;
  className?: string;
  onClick?: () => void;
}

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  action?: ReactNode;
}

interface CardBodyProps {
  children: ReactNode;
  className?: string;
}

interface CardFooterProps {
  children: ReactNode;
  className?: string;
}
```

### Features
- 3 visual variants with different styles
- Glassmorphism effect (elevated)
- Interactive hover states
- Built-in header, body, footer structure
- Icon and action support in header
- Smooth transitions
- TypeScript support

---

## Badge Component

**Location:** `components/ui/badge.tsx`

### Usage

```tsx
import Badge from "@/components/ui/badge";
import { Check } from "lucide-react";

// Basic badge
<Badge>New</Badge>

// Different variants
<Badge variant="default">Default</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="danger">Danger</Badge>
<Badge variant="info">Info</Badge>

// Different sizes
<Badge size="sm">Small</Badge>
<Badge size="md">Medium</Badge>
<Badge size="lg">Large</Badge>

// With icon
<Badge icon={<Check />}>Complete</Badge>

// Custom className
<Badge className="custom-class">Styled</Badge>
```

### Props

```typescript
interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "info";
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
  className?: string;
}
```

### Features
- 5 color variants (default, success, warning, danger, info)
- 3 size options (sm, md, lg)
- Icon support
- Monospace font for data
- Fully rounded (pill-shaped)
- TypeScript support

---

## Design System Variables

All components use CSS variables from the design system in `app/globals.css`:

### Colors
- `--accent` - Primary accent color (theme-aware)
- `--accent-glow` - Glow/secondary accent
- `--accent-muted` - Muted accent
- `--bg-primary` - Primary background
- `--bg-secondary` - Secondary background
- `--text-primary` - Primary text
- `--text-secondary` - Secondary text (improved contrast)
- `--border` - Border color
- `--color-prime` - Blue primary
- `--color-ok` - Success green
- `--color-warn` - Warning amber
- `--color-danger` - Error red

### Spacing Scale
```
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 12px
--spacing-base: 16px
--spacing-lg: 20px
--spacing-xl: 24px
--spacing-2xl: 32px
--spacing-3xl: 40px
--spacing-4xl: 48px
--spacing-5xl: 64px
--spacing-6xl: 80px
--spacing-7xl: 96px
```

### Animation Timing
```
--duration-fast: 200ms
--duration-normal: 300ms
--duration-slow: 500ms
--duration-slower: 700ms
--duration-slowest: 1000ms
--duration-orbit-slow: 12s
--duration-orbit-medium: 14s
--duration-orbit-fast: 16s
```

### Typography
```
--text-display: clamp(2.5rem, 5vw, 4rem)
--text-h1: 2.25rem
--text-h2: 1.875rem
--text-h3: 1.5rem
--text-h4: 1.25rem
--text-body-lg: 1rem
--text-body: 0.9375rem
--text-body-sm: 0.875rem
--text-caption: 0.8125rem
--text-label: 0.75rem
--text-badge: 0.6875rem
--text-code: 0.8125rem
```

---

## Theme Support

All components automatically support the 3 themes:
- **Azul** (Cyan) - Default
- **Esmeralda** (Green)
- **Magenta** (Purple)

Theme is switched via `data-theme` attribute on the HTML element.

---

## Accessibility Features

All components include:
- **Focus Management:** Visible focus rings using CSS focus states
- **ARIA Attributes:** Proper roles, labels, and descriptions
- **Keyboard Support:** Full keyboard navigation support
- **Color Contrast:** WCAG AA compliant text colors
- **Screen Reader Support:** Semantic HTML and proper labels

---

## Best Practices

1. **Use CSS variables:** Don't hardcode colors, use `text-[var(--accent)]`
2. **Follow spacing scale:** Use `p-4`, `gap-3`, etc. (not arbitrary values)
3. **Consistent sizing:** Use named size props (sm, md, lg) instead of hardcoding
4. **Accessibility first:** Always add labels and ARIA attributes
5. **Type safety:** Use TypeScript interfaces for all props
6. **Component composition:** Build UIs from smaller components

---

## Migration Guide

If you're replacing old components with new ones:

1. **Old buttons** → Use new `Button` component with appropriate variant
2. **Old cards** → Use new `Card` with `CardHeader`, `CardBody`, `CardFooter`
3. **Old badges** → Use new `Badge` component with variant
4. **Hardcoded colors** → Replace with CSS variables
5. **Arbitrary spacing** → Use consistent spacing scale

---

## Future Improvements

- [ ] Add Input component
- [ ] Add Select/Dropdown component
- [ ] Add Dialog/Modal component
- [ ] Add Toast notifications (already exists, can be enhanced)
- [ ] Add Tabs component
- [ ] Add Accordion component
- [ ] Create Storybook for visual documentation
- [ ] Add more complex components (DataTable, Form, etc.)

