import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Button,
  Tag,
  Tile,
  SkeletonText,
  ToastNotification,
  Layer,
  Grid,
  Column,
  OrderedList,
  ListItem,
  TextInput,
  Modal,
} from '@carbon/react'
import { Add, TrashCan, LogoYoutube, LogoLinkedin, LogoFacebook, LogoInstagram, CheckmarkFilled, User } from '@carbon/icons-react'
import { getAccounts, disconnectAcct, verifyLinkedInToken } from '../api'

const PLATFORM_META = {
  youtube: { label: 'YouTube', color: 'var(--cds-interactive)', tag: 'red', icon: LogoYoutube },
  linkedin: { label: 'LinkedIn', color: '#0077b5', tag: 'blue', icon: LogoLinkedin },
  facebook: { label: 'Meta', color: '#1877f2', tag: 'blue', icon: LogoFacebook },
  instagram: { label: 'Instagram', color: '#e1306c', tag: 'magenta', icon: LogoInstagram },
}

function AccountCard({ account, onDisconnect }) {
  const [confirming, setConfirming] = useState(false)
  const platformMeta = PLATFORM_META[account.platform] || PLATFORM_META.youtube
  const Icon = platformMeta.icon

  return (
    <Layer>
      <Tile style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {/* Avatar */}
          <div style={{ position: 'relative', flexShrink: 0 }}>
            {account.thumbnail ? (
              <img
                src={account.thumbnail}
                alt={account.account_name}
                style={{ width: 52, height: 52, borderRadius: '50%', objectFit: 'cover' }}
              />
            ) : (
              <div style={{
                width: 52, height: 52, borderRadius: '50%',
                background: platformMeta.color,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon size={24} style={{ color: '#fff' }} />
              </div>
            )}
            <CheckmarkFilled
              size={16}
              style={{
                position: 'absolute', bottom: 0, right: 0,
                color: 'var(--cds-support-success)',
                background: 'var(--cds-background)',
                borderRadius: '50%',
              }}
            />
          </div>

          {/* Info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ margin: 0, fontWeight: 600, fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {account.account_name}
            </p>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>
              {account.platform === 'youtube' && `${parseInt(account.subscribers || 0).toLocaleString()} subscribers`}
              {account.platform === 'linkedin' && account.email}
              {account.platform === 'facebook' && `${parseInt(account.followers || 0).toLocaleString()} followers`}
              {account.platform === 'instagram' && (account.page_name ? `Linked Page: ${account.page_name}` : 'Instagram Business')}
            </p>
          </div>

          {/* Tag */}
          <Tag type={platformMeta.tag} renderIcon={Icon}>
            {platformMeta.label}
          </Tag>

          {/* Actions */}
          {confirming ? (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <Button
                size="sm" kind="danger"
                onClick={() => { onDisconnect(account.platform, account.account_id); setConfirming(false) }}
              >
                Confirm
              </Button>
              <Button size="sm" kind="secondary" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              size="sm" kind="danger--ghost"
              renderIcon={TrashCan}
              onClick={() => setConfirming(true)}
            >
              Disconnect
            </Button>
          )}
        </div>
      </Tile>
    </Layer>
  )
}

export default function Connect() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading]   = useState(true)
  const [toast, setToast]       = useState(null)
  const [searchParams]          = useSearchParams()
  
  const [igModalOpen, setIgModalOpen] = useState(false)
  const [igUsername, setIgUsername]   = useState('')
  const [igPassword, setIgPassword]   = useState('')
  const [ig2faCode, setIg2faCode]     = useState('')
  const [igNeeds2fa, setIgNeeds2fa]   = useState(false)
  const [igLoading, setIgLoading]     = useState(false)

  const load = async () => {
    setLoading(true)
    try { setAccounts(await getAccounts()) } catch {}
    setLoading(false)
  }

  useEffect(() => {
    load()
    const success = searchParams.get('success')
    const error   = searchParams.get('error')
    const channel = searchParams.get('channel')
    const platform = searchParams.get('platform')
    if (success) {
        const pStr = PLATFORM_META[platform]?.label || 'Account'
        setToast({ msg: `Connected ${pStr}: ${decodeURIComponent(channel || 'account')}`, kind: 'success' })
    }
    if (error) setToast({ msg: decodeURIComponent(error), kind: 'error' })
  }, [])

  const handleDisconnect = async (platform, id) => {
    try {
        await disconnectAcct(platform, id)
        setToast({ msg: 'Account disconnected', kind: 'info' })
        load()
    } catch (err) {
        setToast({ msg: `Failed to disconnect: ${err.message}`, kind: 'error' })
    }
  }

  const handleDisconnectAll = async () => {
    if (!window.confirm('Are you sure you want to disconnect ALL accounts?')) return
    
    setLoading(true)
    for (const acct of accounts) {
      try { await disconnectAcct(acct.platform, acct.account_id) } catch {}
    }
    setToast({ msg: 'All accounts disconnected', kind: 'info' })
    load()
  }

  const handleManualVerify = async () => {
    if (!manualToken) return
    setManualLoading(true)
    try {
      let res
      if (manualPlatform === 'linkedin') {
        res = await verifyLinkedInToken(manualToken)
        setToast({ msg: `LinkedIn Connected: ${res.name}`, kind: 'success' })
      } else {
        // Instagram or Facebook
        const uri = manualPlatform === 'instagram' ? '/api/auth/instagram/verify' : '/api/auth/facebook/verify'
        res = await fetch(uri, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: `token=${encodeURIComponent(manualToken)}`
        }).then(r => r.json())
        
        if (res.error || res.detail) throw new Error(res.error || res.detail)
        setToast({ msg: `${manualPlatform === 'facebook' ? 'Facebook' : 'Instagram'} Connected: ${res.name || res.username}`, kind: 'success' })
      }
      setLiModalOpen(false)
      setManualToken('')
      load()
    } catch (err) {
      setToast({ msg: `Failed to verify: ${err.message}`, kind: 'error' })
    }
    setManualLoading(false)
  }

  const handleInstagramConnect = async () => {
    if (!igUsername || !igPassword) return
    setIgLoading(true)
    try {
      const body = new URLSearchParams({
        username: igUsername.trim(),
        password: igPassword,
        verification_code: ig2faCode.trim(),
      })
      const res = await fetch('/api/auth/instagram/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString()
      }).then(r => r.json())

      if (res.requires_2fa) {
        setIgNeeds2fa(true)
        setIgLoading(false)
        return
      }
      if (res.detail) throw new Error(res.detail)

      setToast({ msg: `Instagram Connected: @${res.username}`, kind: 'success' })
      setIgModalOpen(false)
      setIgUsername(''); setIgPassword(''); setIg2faCode(''); setIgNeeds2fa(false)
      load()
    } catch (err) {
      setToast({ msg: `Instagram error: ${err.message}`, kind: 'error' })
    }
    setIgLoading(false)
  }

  const ytSteps = [
    'Click "Connect YouTube Account"',
    'Choose your Google account',
    'Click Allow on permissions screen',
    "Account appears in list below",
  ]
  
  const liSteps = [
    'Go to LinkedIn Developer Portal',
    'Get an Access Token (OAuth2)',
    'Click "Connect LinkedIn" below',
    'Paste token and click Connect',
  ]

  const metaSteps = [
    'Click "Connect Meta Account"',
    'Approve Facebook Page and Instagram permissions',
    'Your Facebook Pages are imported automatically',
    'Any linked Instagram Business accounts appear too',
  ]

  return (
    <Grid>
      <Column lg={10} md={8} sm={4}>
        {toast && (
          <div style={{ position: 'fixed', top: '3.5rem', right: '1rem', zIndex: 9000 }}>
            <ToastNotification
              kind={toast.kind}
              title={toast.msg}
              timeout={4000}
              onClose={() => setToast(null)}
            />
          </div>
        )}

        <h1 style={{ marginBottom: '0.5rem' }}>Connected Accounts</h1>
        <p style={{ color: 'var(--cds-text-secondary)', marginBottom: '2rem' }}>
          Connect your social accounts to start scheduling posts globally.
        </p>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2.5rem', flexWrap: 'wrap' }}>
          <Button
            renderIcon={LogoFacebook}
            onClick={() => { window.location.href = '/api/auth/facebook/login' }}
            kind="primary"
          >
            Connect Meta Account (FB/IG)
          </Button>

          <Button
            renderIcon={LogoInstagram}
            onClick={() => setIgModalOpen(true)}
            kind="tertiary"
          >
            Instagram Login (User/Pass)
          </Button>
          
          <Button
            renderIcon={LogoYoutube}
            onClick={() => { window.location.href = '/api/auth/login' }}
            kind="secondary"
          >
            Connect YouTube
          </Button>
          
          <Button
            renderIcon={LogoLinkedin}
            onClick={() => { window.location.href = '/api/auth/linkedin/login' }}
            kind="secondary"
          >
            Connect LinkedIn Account
          </Button>
        </div>

        <p style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', marginBottom: '2rem' }}>
            Manual token setup? <Button kind="ghost" size="sm" onClick={() => setLiModalOpen(true)} style={{ padding: '0 4px', minHeight: 'auto' }}>Click here</Button>
        </p>

        {/* Info Tiles */}
        <Grid narrow style={{ marginBottom: '2rem', marginLeft: 0, padding: 0 }}>
          <Column lg={8} md={4} sm={4}>
            <Tile>
               <h4 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                 <LogoYoutube /> YouTube Setup
               </h4>
               <OrderedList>
                {ytSteps.map((s, i) => <ListItem key={i}>{s}</ListItem>)}
              </OrderedList>
            </Tile>
          </Column>
          <Column lg={8} md={4} sm={4}>
            <Tile>
               <h4 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                 <LogoLinkedin /> LinkedIn Setup
               </h4>
               <OrderedList>
                {liSteps.map((s, i) => <ListItem key={i}>{s}</ListItem>)}
              </OrderedList>
            </Tile>
          </Column>
          <Column lg={8} md={4} sm={4}>
            <Tile>
               <h4 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                 <LogoFacebook /> Meta + Instagram Setup
               </h4>
               <OrderedList>
                {metaSteps.map((s, i) => <ListItem key={i}>{s}</ListItem>)}
              </OrderedList>
            </Tile>
          </Column>
        </Grid>

        {/* Instagram Connect Modal — username + password */}
        <Modal
            open={igModalOpen}
            modalHeading="Connect Instagram Account"
            primaryButtonText={igLoading ? "Connecting..." : (igNeeds2fa ? "Verify Code" : "Connect")}
            secondaryButtonText="Cancel"
            onRequestClose={() => {
              setIgModalOpen(false)
              setIgUsername(''); setIgPassword(''); setIg2faCode(''); setIgNeeds2fa(false)
            }}
            onRequestSubmit={handleInstagramConnect}
            primaryButtonDisabled={igLoading || (!igNeeds2fa && (!igUsername || !igPassword)) || (igNeeds2fa && !ig2faCode)}
        >
            <div>
              {/* Header */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                padding: '1rem 1.25rem',
                background: 'linear-gradient(135deg, #833ab4 0%, #fd1d1d 50%, #fcb045 100%)',
                borderRadius: '8px', marginBottom: '1.5rem'
              }}>
                <LogoInstagram size={32} style={{ color: '#fff', flexShrink: 0 }} />
                <div>
                  <p style={{ margin: 0, color: '#fff', fontWeight: 600, fontSize: '1rem' }}>Instagram Login</p>
                  <p style={{ margin: 0, color: 'rgba(255,255,255,0.85)', fontSize: '0.75rem' }}>
                    Enter your Instagram credentials
                  </p>
                </div>
              </div>

              {!igNeeds2fa ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <TextInput
                    id="ig-username"
                    labelText="Instagram Username"
                    placeholder="e.g. mypostscheduler"
                    value={igUsername}
                    onChange={e => setIgUsername(e.target.value)}
                    autoComplete="username"
                  />
                  <TextInput
                    id="ig-password"
                    labelText="Password"
                    placeholder="Your Instagram password"
                    type="password"
                    value={igPassword}
                    onChange={e => setIgPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>
                    🔒 Your credentials are used only to authenticate with Instagram and are never stored on our servers.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <p style={{ margin: 0, fontSize: '0.875rem' }}>
                    Instagram sent a verification code to your phone or email. Enter it below.
                  </p>
                  <TextInput
                    id="ig-2fa"
                    labelText="Verification Code"
                    placeholder="6-digit code"
                    value={ig2faCode}
                    onChange={e => setIg2faCode(e.target.value)}
                    autoComplete="one-time-code"
                  />
                </div>
              )}
            </div>
        </Modal>


        {/* Accounts list */}
        {loading ? (
          <>
            <SkeletonText paragraph lines={3} style={{ marginBottom: '1rem' }} />
            <SkeletonText paragraph lines={3} />
          </>
        ) : accounts.length === 0 ? (
          <Tile style={{ textAlign: 'center', padding: '3rem 1rem', border: '2px dashed var(--cds-border-subtle)' }}>
            <User size={40} style={{ color: 'var(--cds-text-secondary)', marginBottom: '0.5rem' }} />
            <p style={{ color: 'var(--cds-text-secondary)', margin: 0 }}>No accounts connected yet</p>
          </Tile>
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <p style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)', margin: 0 }}>
                {accounts.length} account{accounts.length > 1 ? 's' : ''} connected
                </p>
                <Button kind="danger--ghost" size="sm" onClick={handleDisconnectAll}>
                    Disconnect All
                </Button>
            </div>
            {accounts.map(a => (
              <AccountCard key={`${a.platform}-${a.account_id}`} account={a} onDisconnect={handleDisconnect} />
            ))}
          </>
        )}
      </Column>
    </Grid>
  )
}
