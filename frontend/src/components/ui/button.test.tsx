import { render, screen } from '@testing-library/react'
import { Button } from './button'

describe('Button Component', () => {
  it('renders button with default variant', () => {
    render(<Button>Click me</Button>)
    
    const button = screen.getByRole('button', { name: /click me/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('bg-primary')
  })

  it('renders button with secondary variant', () => {
    render(<Button variant="secondary">Secondary</Button>)
    
    const button = screen.getByRole('button', { name: /secondary/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('bg-secondary')
  })

  it('renders button with outline variant', () => {
    render(<Button variant="outline">Outline</Button>)
    
    const button = screen.getByRole('button', { name: /outline/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('border-input')
  })

  it('renders disabled button', () => {
    render(<Button disabled>Disabled</Button>)
    
    const button = screen.getByRole('button', { name: /disabled/i })
    expect(button).toBeInTheDocument()
    expect(button).toBeDisabled()
  })

  it('renders button with different sizes', () => {
    render(<Button size="sm">Small</Button>)
    
    const button = screen.getByRole('button', { name: /small/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('h-9')
  })
})