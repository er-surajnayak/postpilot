import { useState, useEffect, useRef } from 'react'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import {
  Box, Typography, Button, Card, CardContent, CardActionArea,
  TextField, Select, MenuItem, FormControl, InputLabel,
  ToggleButton, ToggleButtonGroup, Alert, Stack, Chip, Divider,
  CircularProgress, FormHelperText,
} from '@mui/material'
import CloudUploadIcon    from '@mui/icons-material/CloudUpload'
import VideoFileIcon      from '@mui/icons-material/VideoFile'
import ImageIcon          from '@mui/icons-material/Image'
import ScheduleIcon       from '@mui/icons-material/Schedule'
import FlashOnIcon        from '@mui/icons-material/FlashOn'
import DeleteIcon         from '@mui/icons-material/Delete'
import YouTubeIcon        from '@mui/icons-material/YouTube'
import LinkedInIcon       from '@mui/icons-material/LinkedIn'
import InfoIcon           from '@mui/icons-material/Info'
import { getAccounts, uploadPost } from '../api'

const TIMEZONES = [
  { value: 'Asia/Kolkata',        label: 'IST — India (UTC+5:30)' },
  { value: 'UTC',                 label: 'UTC — Universal' },
  { value: 'America/New_York',    label: 'EST — New York (UTC-5)' },
  { value: 'America/Los_Angeles', label: 'PST — Los Angeles (UTC-8)' },
  { value: 'Europe/London',       label: 'GMT — London (UTC+0)' },
  { value: 'Asia/Tokyo',          label: 'JST — Tokyo (UTC+9)' },
  { value: 'Asia/Singapore',      label: 'SGT — Singapore (UTC+8)' },
]

const PRIVACY = [
  { value: 'private',  label: 'Private',  desc: 'Only you', icon: '🔒' },
  { value: 'unlisted', label: 'Unlisted', desc: 'Anyone with link', icon: '🔗' },
  { value: 'public',   label: 'Public',   desc: 'Everyone', icon: '🌍' },
]

export default function Compose() {
  const [platform,     setPlatform]     = useState('youtube')
  const [accounts,     setAccounts]     = useState([])
  const [accountId,    setAccountId]    = useState('')
  const [title,        setTitle]        = useState('')
  const [message,      setMessage]      = useState('')
  const [description,  setDescription]  = useState('')
  const [tags,         setTags]         = useState('')
  const [privacy,      setPrivacy]      = useState('private')
  const [isShort,      setIsShort]      = useState(false)
  const [scheduleMode, setScheduleMode] = useState('now')
  const [scheduleDate, setScheduleDate] = useState(new Date(Date.now() + 3600000))
  const [timezone,     setTimezone]     = useState('Asia/Kolkata')
  
  const [mediaFile,    setMediaFile]    = useState(null)
  const [mediaPreview, setMediaPreview] = useState(null)
  const [mediaType,    setMediaType]    = useState(null) // 'image' or 'video'
  
  const [thumbFile,    setThumbFile]    = useState(null)
  const [thumbPreview, setThumbPreview] = useState(null)
  
  const [submitting,   setSubmitting]   = useState(false)
  const [result,       setResult]       = useState(null)
  const [error,        setError]        = useState(null)

  const mediaRef = useRef()
  const thumbRef = useRef()

  useEffect(() => {
    getAccounts().then(a => {
      setAccounts(a)
      // find first account for selected platform
      const first = a.find(acc => acc.platform === platform)
      if (first) setAccountId(first.account_id)
      else setAccountId('')
    }).catch(() => {})
  }, [platform])

  const onMediaChange = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setMediaFile(f)
    setMediaPreview(URL.createObjectURL(f))
    setMediaType(f.type.startsWith('video/') ? 'video' : 'image')
  }

  const onThumbChange = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setThumbFile(f)
    setThumbPreview(URL.createObjectURL(f))
  }

  const handlePlatformChange = (p) => {
    if (!p) return
    setPlatform(p)
    // clear media if it doesn't fit (YouTube MUST be video)
    if (p === 'youtube' && mediaType === 'image') {
        setMediaFile(null)
        setMediaPreview(null)
        setMediaType(null)
    }
  }

  const handleSubmit = async () => {
    if (!accountId) return setError(`Please connect a ${platform} account first.`)
    
    if (platform === 'youtube') {
        if (!title.trim()) return setError('Please enter a video title.')
        if (!mediaFile || mediaType !== 'video') return setError('Please select a video file for YouTube.')
    } else {
        if (!message.trim()) return setError('Please enter a message for LinkedIn.')
    }

    setError(null); setSubmitting(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('platform',    platform)
      fd.append('account_id',  accountId)
      fd.append('title',       title)
      fd.append('message',     message)
      fd.append('description', description)
      fd.append('tags',        tags)
      fd.append('privacy',     privacy)
      fd.append('is_short',    isShort)
      fd.append('timezone',    timezone)
      
      if (scheduleMode === 'later') fd.append('scheduled_at', scheduleDate.toISOString())
      
      if (mediaFile) {
        if (mediaType === 'video') fd.append('video', mediaFile)
        else fd.append('image', mediaFile)
      }
      
      if (thumbFile) fd.append('thumbnail', thumbFile)

      const res = await uploadPost(fd)
      setResult(res)
      setTitle(''); setMessage(''); setDescription(''); setTags('')
      setMediaFile(null); setMediaPreview(null); setMediaType(null)
      setThumbFile(null); setThumbPreview(null)
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed. Please try again.')
    }
    setSubmitting(false)
  }

  const filteredAccounts = accounts.filter(a => a.platform === platform)

  return (
    <Box sx={{ maxWidth: 700 }}>
      <Typography variant="h4" gutterBottom>New Post</Typography>
      <Typography color="text.secondary" sx={{ mb: 4 }}>
        Broadcast your message across platforms effortlessly.
      </Typography>

      {/* Platform Selector */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="caption" fontWeight={700} sx={{ mb: 1, display: 'block', textTransform: 'uppercase', color: 'text.secondary' }}>
            Select Platform
        </Typography>
        <ToggleButtonGroup
            value={platform}
            exclusive
            onChange={(_, v) => handlePlatformChange(v)}
            fullWidth
            sx={{
                bgcolor: 'background.paper',
                '& .MuiToggleButton-root': { py: 1.5, border: '1px solid', borderColor: 'divider' },
                '& .Mui-selected': { bgcolor: 'primary.main', color: '#fff', '&:hover': { bgcolor: 'primary.dark' } }
            }}
        >
            <ToggleButton value="youtube" sx={{ gap: 1 }}>
                <YouTubeIcon sx={{ color: platform === 'youtube' ? '#fff' : '#f00' }} /> YouTube
            </ToggleButton>
            <ToggleButton value="linkedin" sx={{ gap: 1 }}>
                <LinkedInIcon sx={{ color: platform === 'linkedin' ? '#fff' : '#0077b5' }} /> LinkedIn
            </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* No accounts warning */}
      {filteredAccounts.length === 0 && (
        <Alert severity="warning" sx={{ mb: 3 }} icon={<InfoIcon />}>
          No {platform} accounts connected.{' '}
          <a href="/connect" style={{ color: 'inherit', fontWeight: 700 }}>Connect an account →</a>
        </Alert>
      )}

      {result && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {result.status === 'queued' ? 'Post queued!' : 'Processing...'} Job ID:{' '}
          <code>{result.job_id}</code> — Check the Queue tab for status.
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Stack spacing={3}>
        {/* Account selection */}
        <FormControl fullWidth>
          <InputLabel>{platform === 'youtube' ? 'YouTube Channel' : 'LinkedIn Profile'}</InputLabel>
          <Select
            value={accountId}
            label={platform === 'youtube' ? 'YouTube Channel' : 'LinkedIn Profile'}
            onChange={e => setAccountId(e.target.value)}
          >
            {filteredAccounts.length === 0
              ? <MenuItem value="">No {platform} accounts</MenuItem>
              : filteredAccounts.map(a => (
                  <MenuItem key={a.account_id} value={a.account_id}>{a.account_name}</MenuItem>
                ))
            }
          </Select>
        </FormControl>

        {/* Media upload */}
        <Box>
          <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
            Media File (Optional for LinkedIn)
            {mediaFile && <Chip label={`${(mediaFile.size/1024/1024).toFixed(1)} MB`} size="small" sx={{ ml: 1 }} />}
          </Typography>
          <input ref={mediaRef} type="file" accept={platform === 'youtube' ? "video/*" : "image/*,video/*"} onChange={onMediaChange} style={{ display: 'none' }} />
          {mediaPreview ? (
            <Box sx={{ position: 'relative' }}>
               {mediaType === 'video' ? (
                   <video src={mediaPreview} controls style={{ width: '100%', borderRadius: 12, maxHeight: 220, background: '#000' }} />
               ) : (
                   <img src={mediaPreview} alt="" style={{ width: '100%', borderRadius: 12, maxHeight: 220, objectFit: 'contain', background: '#000' }} />
               )}
              <Button
                size="small" variant="contained" color="error"
                startIcon={<DeleteIcon />}
                onClick={() => { setMediaFile(null); setMediaPreview(null); setMediaType(null) }}
                sx={{ position: 'absolute', top: 8, right: 8 }}
              >
                Remove
              </Button>
            </Box>
          ) : (
            <Card
              variant="outlined"
              sx={{ border: '2px dashed', borderColor: 'divider', cursor: 'pointer', '&:hover': { borderColor: 'primary.main' } }}
            >
              <CardActionArea onClick={() => mediaRef.current.click()}>
                <CardContent sx={{ textAlign: 'center', py: 5 }}>
                  <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                  <Typography fontWeight={600}>Click to select {platform === 'youtube' ? 'video' : 'media'}</Typography>
                  <Typography variant="caption" color="text.secondary">
                      {platform === 'youtube' ? 'MP4, MOV, AVI supported' : 'Images or Videos supported'}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          )}
        </Box>

        {/* Platform-specific options */}
        {platform === 'youtube' && (
            <Box>
                <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>Video Type</Typography>
                <ToggleButtonGroup value={isShort} exclusive onChange={(_, v) => v !== null && setIsShort(v)} fullWidth>
                    <ToggleButton value={false} sx={{ textTransform: 'none', fontWeight: 600 }}>🎬 Regular Video</ToggleButton>
                    <ToggleButton value={true}  sx={{ textTransform: 'none', fontWeight: 600 }}>🩳 YouTube Short</ToggleButton>
                </ToggleButtonGroup>
                {isShort && (
                    <FormHelperText>⚠️ Must be ≤60s and vertical (9:16). #Shorts added to title automatically.</FormHelperText>
                )}
            </Box>
        )}

        {/* Content Fields */}
        {platform === 'youtube' ? (
            <>
                <TextField
                  label="Video Title"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  inputProps={{ maxLength: 100 }}
                  helperText={`${title.length}/100`}
                  fullWidth
                />
                <TextField
                  label="Description"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  multiline rows={3}
                  fullWidth
                  helperText="Optional"
                />
                 <TextField
                    label="Tags"
                    value={tags}
                    onChange={e => setTags(e.target.value)}
                    placeholder="tech, tutorial, automation..."
                    helperText="Comma separated"
                    fullWidth
                  />
            </>
        ) : (
            <TextField
                label="Message"
                value={message}
                onChange={e => setMessage(e.target.value)}
                multiline rows={4}
                placeholder="What do you want to share today? #social #media"
                fullWidth
            />
        )}

        {/* YouTube Thumbnail */}
        {platform === 'youtube' && (
            <Box>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                Custom Thumbnail <Typography component="span" variant="caption" color="text.secondary">(Optional)</Typography>
              </Typography>
              <input ref={thumbRef} type="file" accept="image/*" onChange={onThumbChange} style={{ display: 'none' }} />
              {thumbPreview ? (
                <Box sx={{ position: 'relative', display: 'inline-block', width: '100%' }}>
                  <img src={thumbPreview} alt="" style={{ width: '100%', maxHeight: 180, objectFit: 'cover', borderRadius: 12 }} />
                  <Button
                    size="small" variant="contained" color="error"
                    startIcon={<DeleteIcon />}
                    onClick={() => { setThumbFile(null); setThumbPreview(null) }}
                    sx={{ position: 'absolute', top: 8, right: 8 }}
                  >
                    Remove
                  </Button>
                </Box>
              ) : (
                <Card variant="outlined" sx={{ border: '2px dashed', borderColor: 'divider', cursor: 'pointer', '&:hover': { borderColor: 'primary.main' } }}>
                  <CardActionArea onClick={() => thumbRef.current.click()}>
                    <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2 }}>
                      <ImageIcon sx={{ color: 'text.secondary' }} />
                      <Typography variant="body2">Upload custom thumbnail</Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              )}
            </Box>
        )}

        {/* YouTube Privacy */}
        {platform === 'youtube' && (
            <Box>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>Privacy</Typography>
              <Stack direction="row" spacing={1.5}>
                {PRIVACY.map(({ value, label, desc, icon }) => (
                  <Card
                    key={value}
                    onClick={() => setPrivacy(value)}
                    sx={{
                      flex: 1, cursor: 'pointer', textAlign: 'center',
                      border: '2px solid',
                      borderColor: privacy === value ? 'primary.main' : 'divider',
                      bgcolor: privacy === value ? 'primary.main' : 'background.paper',
                      transition: 'all 0.15s',
                    }}
                  >
                    <CardContent sx={{ py: '12px !important' }}>
                      <Typography fontSize={20}>{icon}</Typography>
                      <Typography fontWeight={700} fontSize={13} color={privacy === value ? '#fff' : 'text.primary'}>{label}</Typography>
                      <Typography variant="caption" color={privacy === value ? 'rgba(255,255,255,0.8)' : 'text.secondary'}>{desc}</Typography>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            </Box>
        )}

        {/* Schedule */}
        <Box>
          <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>When to publish?</Typography>
          <ToggleButtonGroup value={scheduleMode} exclusive onChange={(_, v) => v && setScheduleMode(v)} fullWidth sx={{ mb: 2 }}>
            <ToggleButton value="now"   sx={{ textTransform: 'none', fontWeight: 600, gap: 1 }}>
              <FlashOnIcon fontSize="small" /> Publish immediately
            </ToggleButton>
            <ToggleButton value="later" sx={{ textTransform: 'none', fontWeight: 600, gap: 1 }}>
              <ScheduleIcon fontSize="small" /> Schedule for later
            </ToggleButton>
          </ToggleButtonGroup>

          {scheduleMode === 'later' && (
            <Stack spacing={2}>
              <Box sx={{
                '& .react-datepicker-wrapper': { width: '100%' },
                '& .react-datepicker__input-container input': {
                  width: '100%', padding: '14px', borderRadius: '12px',
                  border: '1px solid', borderColor: 'divider',
                  background: 'transparent', color: 'inherit',
                  fontSize: 14, outline: 'none', fontFamily: 'inherit',
                },
              }}>
                <DatePicker
                  selected={scheduleDate}
                  onChange={setScheduleDate}
                  showTimeSelect timeIntervals={15}
                  dateFormat="MMMM d, yyyy h:mm aa"
                  minDate={new Date()}
                  placeholderText="Pick date and time"
                />
              </Box>
              <FormControl fullWidth>
                <InputLabel>Timezone</InputLabel>
                <Select value={timezone} label="Timezone" onChange={e => setTimezone(e.target.value)}>
                  {TIMEZONES.map(tz => (
                    <MenuItem key={tz.value} value={tz.value}>{tz.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
          )}
        </Box>

        {/* Submit */}
        <Button
          variant="contained"
          size="large"
          onClick={handleSubmit}
          disabled={submitting || filteredAccounts.length === 0}
          startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : (scheduleMode === 'later' ? <ScheduleIcon /> : <CloudUploadIcon />)}
          fullWidth
          sx={{ py: 1.8, fontSize: 16, fontWeight: 700 }}
        >
          {submitting ? 'Processing...' : scheduleMode === 'later' ? 'Schedule Post' : 'Publish Now'}
        </Button>
      </Stack>
    </Box>
  )
}

