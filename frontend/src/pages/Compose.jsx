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
  const [accounts,     setAccounts]     = useState([])
  const [channelId,    setChannelId]    = useState('')
  const [title,        setTitle]        = useState('')
  const [description,  setDescription]  = useState('')
  const [tags,         setTags]         = useState('')
  const [privacy,      setPrivacy]      = useState('private')
  const [isShort,      setIsShort]      = useState(false)
  const [scheduleMode, setScheduleMode] = useState('now')
  const [scheduleDate, setScheduleDate] = useState(new Date(Date.now() + 3600000))
  const [timezone,     setTimezone]     = useState('Asia/Kolkata')
  const [videoFile,    setVideoFile]    = useState(null)
  const [thumbFile,    setThumbFile]    = useState(null)
  const [videoPreview, setVideoPreview] = useState(null)
  const [thumbPreview, setThumbPreview] = useState(null)
  const [submitting,   setSubmitting]   = useState(false)
  const [result,       setResult]       = useState(null)
  const [error,        setError]        = useState(null)

  const videoRef = useRef()
  const thumbRef = useRef()

  useEffect(() => {
    getAccounts().then(a => {
      setAccounts(a)
      if (a.length > 0) setChannelId(a[0].channel_id)
    }).catch(() => {})
  }, [])

  const onVideoChange = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setVideoFile(f)
    setVideoPreview(URL.createObjectURL(f))
  }

  const onThumbChange = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setThumbFile(f)
    setThumbPreview(URL.createObjectURL(f))
  }

  const handleSubmit = async () => {
    if (!channelId) return setError('Please connect a YouTube account first.')
    if (!title.trim()) return setError('Please enter a title.')
    if (!videoFile) return setError('Please select a video file.')
    setError(null); setSubmitting(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('channel_id',  channelId)
      fd.append('title',       title)
      fd.append('description', description)
      fd.append('tags',        tags)
      fd.append('privacy',     privacy)
      fd.append('is_short',    isShort)
      fd.append('timezone',    timezone)
      fd.append('notify',      false)
      if (scheduleMode === 'later') fd.append('scheduled_at', scheduleDate.toISOString())
      fd.append('video', videoFile)
      if (thumbFile) fd.append('thumbnail', thumbFile)
      const res = await uploadPost(fd)
      setResult(res)
      setTitle(''); setDescription(''); setTags('')
      setVideoFile(null); setVideoPreview(null)
      setThumbFile(null); setThumbPreview(null)
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed. Please try again.')
    }
    setSubmitting(false)
  }

  return (
    <Box sx={{ maxWidth: 700 }}>
      <Typography variant="h4" gutterBottom>New Post</Typography>
      <Typography color="text.secondary" sx={{ mb: 4 }}>
        Upload and schedule your video across platforms.
      </Typography>

      {/* No accounts warning */}
      {accounts.length === 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          No accounts connected.{' '}
          <a href="/connect" style={{ color: 'inherit', fontWeight: 700 }}>Connect an account →</a>
        </Alert>
      )}

      {result && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {result.status === 'queued' ? 'Post queued!' : 'Uploading...'} Job ID:{' '}
          <code>{result.job_id}</code> — Check the Queue tab for status.
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Stack spacing={3}>
        {/* Channel */}
        <FormControl fullWidth>
          <InputLabel>YouTube Channel</InputLabel>
          <Select
            value={channelId}
            label="YouTube Channel"
            onChange={e => setChannelId(e.target.value)}
          >
            {accounts.length === 0
              ? <MenuItem value="">No accounts connected</MenuItem>
              : accounts.map(a => (
                  <MenuItem key={a.channel_id} value={a.channel_id}>{a.channel_name}</MenuItem>
                ))
            }
          </Select>
        </FormControl>

        {/* Video upload */}
        <Box>
          <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
            Video File{videoFile && <Chip label={`${(videoFile.size/1024/1024).toFixed(1)} MB`} size="small" sx={{ ml: 1 }} />}
          </Typography>
          <input ref={videoRef} type="file" accept="video/*" onChange={onVideoChange} style={{ display: 'none' }} />
          {videoPreview ? (
            <Box sx={{ position: 'relative' }}>
              <video src={videoPreview} controls style={{ width: '100%', borderRadius: 12, maxHeight: 220, background: '#000' }} />
              <Button
                size="small" variant="contained" color="error"
                startIcon={<DeleteIcon />}
                onClick={() => { setVideoFile(null); setVideoPreview(null) }}
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
              <CardActionArea onClick={() => videoRef.current.click()}>
                <CardContent sx={{ textAlign: 'center', py: 5 }}>
                  <VideoFileIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                  <Typography fontWeight={600}>Click to select video</Typography>
                  <Typography variant="caption" color="text.secondary">MP4, MOV, AVI, MKV supported</Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          )}
        </Box>

        {/* Video type */}
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

        {/* Title */}
        <TextField
          label="Title"
          value={title}
          onChange={e => setTitle(e.target.value)}
          inputProps={{ maxLength: 100 }}
          helperText={`${title.length}/100`}
          placeholder={isShort ? 'Short title (#Shorts added automatically)' : 'Enter video title...'}
          fullWidth
        />

        {/* Description */}
        <TextField
          label="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
          multiline rows={3}
          placeholder="Video description..."
          helperText="Optional"
          fullWidth
        />

        {/* Tags */}
        <TextField
          label="Tags"
          value={tags}
          onChange={e => setTags(e.target.value)}
          placeholder="tech, tutorial, automation..."
          helperText="Comma separated"
          fullWidth
        />

        {/* Thumbnail */}
        <Box>
          <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
            Thumbnail <Typography component="span" variant="caption" color="text.secondary">(JPG/PNG, 1280×720 recommended)</Typography>
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
                  <Typography variant="body2">Upload thumbnail image</Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>Optional</Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          )}
        </Box>

        {/* Privacy */}
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
          disabled={submitting || accounts.length === 0}
          startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : (scheduleMode === 'later' ? <ScheduleIcon /> : <CloudUploadIcon />)}
          fullWidth
          sx={{ py: 1.8, fontSize: 16, fontWeight: 700 }}
        >
          {submitting ? 'Uploading...' : scheduleMode === 'later' ? 'Schedule Post' : 'Publish Now'}
        </Button>
      </Stack>
    </Box>
  )
}
