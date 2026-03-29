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
  InlineNotification,
  OrderedList,
  ListItem,
} from '@carbon/react'
import { Add, TrashCan, LogoYoutube, CheckmarkFilled } from '@carbon/icons-react'
import { getAccounts, disconnectAcct } from '../api'

function AccountCard({ account, onDisconnect }) {
  const [confirming, setConfirming] = useState(false)

  return (
    <Layer>
      <Tile style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {/* Avatar */}
          <div style={{ position: 'relative', flexShrink: 0 }}>
            {account.thumbnail ? (
              <img
                src={account.thumbnail}
                alt={account.channel_name}
                style={{ width: 52, height: 52, borderRadius: '50%', objectFit: 'cover' }}
              />
            ) : (
              <div style={{
                width: 52, height: 52, borderRadius: '50%',
                background: 'var(--cds-interactive)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <LogoYoutube size={24} style={{ color: '#fff' }} />
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
              {account.channel_name}
            </p>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>
              {parseInt(account.subscribers || 0).toLocaleString()} subscribers · {account.video_count} videos
            </p>
          </div>

          {/* Tag */}
          <Tag type="red" renderIcon={LogoYoutube}>YouTube</Tag>

          {/* Actions */}
          {confirming ? (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <Button
                size="sm" kind="danger"
                onClick={() => { onDisconnect(account.channel_id); setConfirming(false) }}
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
    if (success) setToast({ msg: `Connected: ${decodeURIComponent(channel || 'channel')}`, kind: 'success' })
    if (error)   setToast({ msg: decodeURIComponent(error), kind: 'error' })
  }, [])

  const handleDisconnect = async (id) => {
    await disconnectAcct(id)
    setToast({ msg: 'Account disconnected', kind: 'info' })
    load()
  }

  const steps = [
    'Click "Connect YouTube Account" below',
    'Choose your Google account',
    'Click Allow on the permissions screen',
    "You're done — start scheduling!",
  ]

  return (
    <Grid>
      <Column lg={10} md={8} sm={4}>
        {/* Toast */}
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
          Connect your YouTube channel to start scheduling posts.
        </p>

        {/* Connect button */}
        <Button
          renderIcon={Add}
          onClick={() => { window.location.href = '/api/auth/login' }}
          style={{ marginBottom: '2rem' }}
        >
          Connect YouTube Account
        </Button>

        {/* How it works */}
        <Tile style={{ marginBottom: '2rem' }}>
          <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: 'var(--cds-text-secondary)', textTransform: 'uppercase', marginBottom: '1rem', marginTop: 0 }}>
            How it works
          </p>
          <OrderedList>
            {steps.map((text, i) => (
              <ListItem key={i} style={{ fontSize: '0.875rem' }}>{text}</ListItem>
            ))}
          </OrderedList>
        </Tile>

        {/* Accounts list */}
        {loading ? (
          <>
            <SkeletonText paragraph lines={3} style={{ marginBottom: '1rem' }} />
            <SkeletonText paragraph lines={3} />
          </>
        ) : accounts.length === 0 ? (
          <Tile style={{ textAlign: 'center', padding: '3rem 1rem', border: '2px dashed var(--cds-border-subtle)' }}>
            <Add size={40} style={{ color: 'var(--cds-text-secondary)', marginBottom: '0.5rem' }} />
            <p style={{ color: 'var(--cds-text-secondary)', margin: 0 }}>No accounts connected yet</p>
          </Tile>
        ) : (
          <>
            <p style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)', marginBottom: '1rem' }}>
              {accounts.length} account{accounts.length > 1 ? 's' : ''} connected
            </p>
            {accounts.map(a => (
              <AccountCard key={a.channel_id} account={a} onDisconnect={handleDisconnect} />
            ))}
          </>
        )}
      </Column>
    </Grid>
  )
}
