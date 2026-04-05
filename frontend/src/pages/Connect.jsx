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
import { Add, TrashCan, LogoYoutube, LogoLinkedin, CheckmarkFilled, User } from '@carbon/icons-react'
import { getAccounts, disconnectAcct, verifyLinkedInToken } from '../api'

function AccountCard({ account, onDisconnect }) {
  const [confirming, setConfirming] = useState(false)
  const isYT = account.platform === 'youtube'

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
                background: isYT ? 'var(--cds-interactive)' : '#0077b5',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {isYT ? <LogoYoutube size={24} style={{ color: '#fff' }} /> : <LogoLinkedin size={24} style={{ color: '#fff' }} />}
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
              {isYT ? `${parseInt(account.subscribers || 0).toLocaleString()} subscribers` : account.email}
            </p>
          </div>

          {/* Tag */}
          <Tag type={isYT ? 'red' : 'blue'} renderIcon={isYT ? LogoYoutube : LogoLinkedin}>
            {isYT ? 'YouTube' : 'LinkedIn'}
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
              size="sm" kind="ghost" hasIconOnly
              renderIcon={TrashCan}
              iconDescription="Disconnect"
              onClick={() => setConfirming(true)}
            />
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
  
  const [liModalOpen, setLiModalOpen] = useState(false)
  const [liToken, setLiToken]           = useState('')
  const [liLoading, setLiLoading]     = useState(false)

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
        const pStr = platform === 'linkedin' ? 'LinkedIn' : 'YouTube'
        setToast({ msg: `Connected ${pStr}: ${decodeURIComponent(channel || 'account')}`, kind: 'success' })
    }
    if (error) setToast({ msg: decodeURIComponent(error), kind: 'error' })
  }, [])

  const handleDisconnect = async (platform, id) => {
    await disconnectAcct(platform, id)
    setToast({ msg: 'Account disconnected', kind: 'info' })
    load()
  }

  const handleLiVerify = async () => {
    if (!liToken) return
    setLiLoading(true)
    try {
      const res = await verifyLinkedInToken(liToken)
      setToast({ msg: `LinkedIn Connected: ${res.name}`, kind: 'success' })
      setLiModalOpen(false)
      load()
    } catch (err) {
      setToast({ msg: `Failed to verify: ${err.message}`, kind: 'error' })
    }
    setLiLoading(false)
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

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
          <Button
            renderIcon={LogoYoutube}
            onClick={() => { window.location.href = '/api/auth/login' }}
            kind="primary"
          >
            Connect YouTube Account
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
            Prefer manual token entry? <Button kind="ghost" size="sm" onClick={() => setLiModalOpen(true)} style={{ padding: '0 4px', minHeight: 'auto' }}>Click here</Button>
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
        </Grid>

        {/* Modal for LinkedIn */}
        <Modal
            open={liModalOpen}
            modalHeading="Connect LinkedIn Account"
            primaryButtonText="Verify & Connect"
            secondaryButtonText="Cancel"
            onRequestClose={() => setLiModalOpen(false)}
            onRequestSubmit={handleLiVerify}
            primaryButtonDisabled={!liToken || liLoading}
        >
            <p style={{ marginBottom: '1rem' }}>Paste your LinkedIn Access Token from the Developer Portal.</p>
            <TextInput
                id="li-token"
                labelText="Access Token"
                placeholder="AQX..."
                type="password"
                value={liToken}
                onChange={e => setLiToken(e.target.value)}
            />
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
            <p style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)', marginBottom: '1rem' }}>
              {accounts.length} account{accounts.length > 1 ? 's' : ''} connected
            </p>
            {accounts.map(a => (
              <AccountCard key={`${a.platform}-${a.account_id}`} account={a} onDisconnect={handleDisconnect} />
            ))}
          </>
        )}
      </Column>
    </Grid>
  )
}

