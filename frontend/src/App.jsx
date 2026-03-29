import { useState, useMemo } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import {
  Theme,
  Header,
  HeaderContainer,
  HeaderGlobalAction,
  HeaderGlobalBar,
  HeaderMenuButton,
  HeaderName,
  SideNav,
  SideNavItems,
  SideNavLink,
  Content,
  SkipToContent,
} from '@carbon/react'
import { Asleep, Light, UserAvatar, Add, List } from '@carbon/icons-react'

import Connect from './pages/Connect'
import Compose from './pages/Compose'
import Queue   from './pages/Queue'

const NAV = [
  { to: '/connect', label: 'Accounts', Icon: UserAvatar },
  { to: '/compose', label: 'New Post', Icon: Add },
  { to: '/queue',   label: 'Queue',    Icon: List },
]

function AppShell({ mode, toggleMode }) {
  const location = useLocation()
  const navigate = useNavigate()

  const muiTheme = useMemo(() => createTheme({
    palette: {
      mode: mode === 'dark' ? 'dark' : 'light',
      ...(mode === 'dark' && {
        background: {
          default: 'transparent',
          paper: '#262626', // matches carbon's layer-01 for dark themes
        },
      }),
    },
    typography: {
      fontFamily: '"IBM Plex Sans", "Roboto", "Helvetica Neue", Arial, sans-serif',
    },
  }), [mode])

  const isActive = (to) =>
    to === '/connect'
      ? location.pathname === '/' || location.pathname === '/connect'
      : location.pathname === to

  return (
    <HeaderContainer
      render={({ isSideNavExpanded, onClickSideNavExpand }) => (
        <>
          <Header aria-label="PostPilot Social Scheduler">
            <SkipToContent />
            <HeaderMenuButton
              aria-label={isSideNavExpanded ? 'Close menu' : 'Open menu'}
              onClick={onClickSideNavExpand}
              isActive={isSideNavExpanded}
            />
            <HeaderName prefix="">
              Post<strong>Pilot</strong>
            </HeaderName>
            <HeaderGlobalBar>
              <HeaderGlobalAction
                aria-label={mode === 'dark' ? 'Switch to Light' : 'Switch to Dark'}
                onClick={toggleMode}
                tooltipAlignment="end"
              >
                {mode === 'dark' ? <Light size={20} /> : <Asleep size={20} />}
              </HeaderGlobalAction>
            </HeaderGlobalBar>
          </Header>

          <SideNav
            aria-label="Side navigation"
            expanded={isSideNavExpanded}
            onOverlayClick={onClickSideNavExpand}
          >
            <SideNavItems>
              {NAV.map(({ to, label, Icon }) => (
                <SideNavLink
                  key={to}
                  renderIcon={Icon}
                  isActive={isActive(to)}
                  onClick={(e) => {
                    e.preventDefault()
                    navigate(to)
                    if (isSideNavExpanded) onClickSideNavExpand()
                  }}
                  href={to}
                >
                  {label}
                </SideNavLink>
              ))}
            </SideNavItems>
          </SideNav>

            <Theme theme={mode === 'dark' ? 'g100' : 'white'}>
              <ThemeProvider theme={muiTheme}>
                <Content>
                  <Routes>
                    <Route path="/"        element={<Connect />} />
                    <Route path="/connect" element={<Connect />} />
                    <Route path="/compose" element={<Compose />} />
                    <Route path="/queue"   element={<Queue />} />
                  </Routes>
                </Content>
              </ThemeProvider>
            </Theme>
        </>
      )}
    />
  )
}

export default function App() {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('colorMode') : null
  const [mode, setMode] = useState(stored || 'light')

  const toggleMode = () => {
    const next = mode === 'dark' ? 'light' : 'dark'
    setMode(next)
    localStorage.setItem('colorMode', next)
  }

  const carbonTheme = mode === 'dark' ? 'g100' : 'white'

  return (
    <Theme theme={carbonTheme}>
      <BrowserRouter>
        <AppShell mode={mode} toggleMode={toggleMode} />
      </BrowserRouter>
    </Theme>
  )
}
