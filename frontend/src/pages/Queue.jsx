import { useState, useEffect } from 'react'
import {
  Button,
  Tag,
  Tile,
  Layer,
  SkeletonText,
  InlineNotification,
  Grid,
  Column,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
} from '@carbon/react'
import {
  Renew,
  ChevronDown,
  ChevronUp,
  Launch,
  Close,
  LogoYoutube,
  Add,
} from '@carbon/icons-react'
import { getPosts, cancelPost } from '../api'

const STATUS_CONFIG = {
  queued:    { type: 'warm-gray', label: 'Queued'    },
  uploading: { type: 'blue',      label: 'Uploading' },
  scheduled: { type: 'purple',    label: 'Scheduled' },
  published: { type: 'green',     label: 'Published' },
  failed:    { type: 'red',       label: 'Failed'    },
}

const STATUS_ORDER = ['all', 'queued', 'uploading', 'scheduled', 'published', 'failed']

function PostCard({ post, onCancel }) {
  const [expanded,   setExpanded]   = useState(false)
  const [cancelling, setCancelling] = useState(false)

  const canCancel = ['queued', 'scheduled'].includes(post.status)
  const cfg = STATUS_CONFIG[post.status] || STATUS_CONFIG.queued

  const handleCancel = async () => {
    setCancelling(true)
    await cancelPost(post.job_id)
    onCancel(post.job_id)
  }

  const scheduledDate = post.post_data?.scheduled_at
    ? new Date(post.post_data.scheduled_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    : null

  const createdDate = new Date(post.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })

  const detailRows = [
    ['Job ID',   post.job_id],
    ['Privacy',  post.post_data?.privacy?.toUpperCase() || '—'],
    ['Channel',  post.channel_id],
    ['Timezone', post.post_data?.timezone || '—'],
    ['Tags',     post.post_data?.tags?.join(', ') || 'None'],
    ['Video ID', post.video_id || 'Pending…'],
  ]

  return (
    <Layer>
      <Tile style={{ marginBottom: '1rem', padding: 0, overflow: 'hidden' }}>
        {/* Main row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', flexWrap: 'wrap' }}>
          {/* Icon */}
          <div style={{
            width: 44, height: 44, borderRadius: 4, flexShrink: 0,
            background: '#ff0000',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <LogoYoutube size={20} style={{ color: '#fff' }} />
          </div>

          {/* Info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ margin: 0, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {post.post_data?.title || post.title || 'Untitled'}
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginTop: '0.25rem' }}>
              <Tag type={cfg.type} size="sm">{cfg.label}</Tag>
              {scheduledDate && (
                <span style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>📅 {scheduledDate}</span>
              )}
              {post.post_data?.is_short && <Tag type="purple" size="sm">Short</Tag>}
              <span style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>{createdDate}</span>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '0.25rem', flexShrink: 0 }}>
            {post.video_url && (
              <Button
                size="sm" kind="ghost" hasIconOnly
                renderIcon={Launch}
                iconDescription="Watch on YouTube"
                href={post.video_url}
                target="_blank"
                rel="noreferrer"
              />
            )}
            {canCancel && (
              <Button
                size="sm" kind="ghost" hasIconOnly
                renderIcon={Close}
                iconDescription="Cancel"
                onClick={handleCancel}
                disabled={cancelling}
              />
            )}
            <Button
              size="sm" kind="ghost" hasIconOnly
              renderIcon={expanded ? ChevronUp : ChevronDown}
              iconDescription={expanded ? 'Collapse' : 'Expand'}
              onClick={() => setExpanded(!expanded)}
            />
          </div>
        </div>

        {/* Expanded details */}
        {expanded && (
          <div style={{
            borderTop: '1px solid var(--cds-border-subtle)',
            padding: '1rem',
            background: 'var(--cds-layer-accent)',
          }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
            }}>
              {detailRows.map(([k, v]) => (
                <div key={k}>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>{k}</p>
                  <p style={{
                    margin: 0,
                    fontSize: k === 'Job ID' ? '0.7rem' : '0.875rem',
                    fontWeight: 500,
                    wordBreak: 'break-all',
                    fontFamily: ['Job ID', 'Video ID', 'Channel'].includes(k) ? 'monospace' : 'inherit',
                  }}>
                    {v}
                  </p>
                </div>
              ))}
            </div>

            {post.error && (
              <InlineNotification
                kind="error"
                title="Error:"
                subtitle={post.error}
                hideCloseButton
                style={{ marginTop: '1rem', maxWidth: '100%' }}
              />
            )}
            {post.video_url && (
              <div style={{ marginTop: '1rem' }}>
                <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>Video URL</p>
                <a
                  href={post.video_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '0.8rem', wordBreak: 'break-all', color: 'var(--cds-link-primary)' }}
                >
                  {post.video_url}
                </a>
              </div>
            )}
          </div>
        )}
      </Tile>
    </Layer>
  )
}

export default function Queue() {
  const [posts,   setPosts]   = useState([])
  const [loading, setLoading] = useState(true)
  const [tabIdx,  setTabIdx]  = useState(0)

  const load = async () => {
    setLoading(true)
    try {
      const data = await getPosts()
      setPosts(data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)))
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleCancel = (jobId) => setPosts(prev => prev.filter(p => p.job_id !== jobId))

  const stats = [
    { label: 'Total',     value: posts.length,                                    color: 'var(--cds-text-primary)' },
    { label: 'Scheduled', value: posts.filter(p => p.status === 'scheduled').length, color: 'var(--cds-support-info)' },
    { label: 'Published', value: posts.filter(p => p.status === 'published').length, color: 'var(--cds-support-success)' },
    { label: 'Failed',    value: posts.filter(p => p.status === 'failed').length,    color: 'var(--cds-support-error)' },
  ]

  const filterKey  = STATUS_ORDER[tabIdx]
  const filtered   = filterKey === 'all' ? posts : posts.filter(p => p.status === filterKey)

  const tabLabel = (key) => {
    const count = key === 'all' ? posts.length : posts.filter(p => p.status === key).length
    const label = key.charAt(0).toUpperCase() + key.slice(1)
    return count > 0 ? `${label} (${count})` : label
  }

  return (
    <Grid>
      <Column lg={12} md={8} sm={4}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ marginBottom: '0.5rem' }}>Post Queue</h1>
            <p style={{ color: 'var(--cds-text-secondary)', margin: 0 }}>
              Track all your scheduled and published videos.
            </p>
          </div>
          <Button
            kind="secondary"
            renderIcon={Renew}
            onClick={load}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>

        {/* Stats */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem',
        }}>
          {stats.map(({ label, value, color }) => (
            <Layer key={label}>
              <Tile>
                <p style={{ margin: 0, fontSize: '2rem', fontWeight: 800, color }}>{value}</p>
                <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>{label}</p>
              </Tile>
            </Layer>
          ))}
        </div>

        {/* Tabs + posts */}
        <Tabs
          selectedIndex={tabIdx}
          onChange={({ selectedIndex }) => setTabIdx(selectedIndex)}
        >
          <TabList aria-label="Filter posts" contained scrollable>
            {STATUS_ORDER.map(key => (
              <Tab key={key}>{tabLabel(key)}</Tab>
            ))}
          </TabList>
          <TabPanels>
            {STATUS_ORDER.map((key, idx) => (
              <TabPanel key={key} style={{ padding: '1.5rem 0 0' }}>
                {loading ? (
                  <>
                    <SkeletonText paragraph lines={4} style={{ marginBottom: '1rem' }} />
                    <SkeletonText paragraph lines={4} style={{ marginBottom: '1rem' }} />
                    <SkeletonText paragraph lines={4} />
                  </>
                ) : filtered.length === 0 ? (
                  <Tile style={{ textAlign: 'center', padding: '4rem 1rem', border: '2px dashed var(--cds-border-subtle)' }}>
                    <Add size={40} style={{ color: 'var(--cds-text-secondary)', marginBottom: '0.5rem' }} />
                    <p style={{ color: 'var(--cds-text-secondary)', margin: 0 }}>
                      {filterKey === 'all' ? 'No posts yet' : `No ${filterKey} posts`}
                    </p>
                    {filterKey === 'all' && (
                      <Button kind="ghost" href="/compose" style={{ marginTop: '0.5rem' }}>
                        Create your first post →
                      </Button>
                    )}
                  </Tile>
                ) : (
                  filtered.map(post => (
                    <PostCard key={post.job_id} post={post} onCancel={handleCancel} />
                  ))
                )}
              </TabPanel>
            ))}
          </TabPanels>
        </Tabs>
      </Column>
    </Grid>
  )
}
